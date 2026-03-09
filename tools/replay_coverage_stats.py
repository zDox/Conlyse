from __future__ import annotations

import argparse
import json
import logging
import multiprocessing
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Iterable, List, Optional, Sequence, Tuple

from conflict_interface.replay.replay_timeline import ReplayTimeline

try:
    from tqdm import tqdm  # type: ignore[import]
except Exception:  # pragma: no cover - optional dependency
    tqdm = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass
class CoverageInterval:
    start: datetime
    end: datetime
    duration_seconds: float


@dataclass
class ReplayStats:
    file_path: Path

    game_id: Optional[int]
    player_id: Optional[int]
    scenario_id: Optional[int]
    day_of_game: Optional[int]
    speed: Optional[int]
    segment_count: Optional[int]
    game_ended: Optional[bool]

    game_start: Optional[datetime]
    game_end: Optional[datetime]
    total_game_seconds: float

    first_patch_time: Optional[datetime]
    last_patch_time: Optional[datetime]
    patch_span_seconds: float
    total_patches: int

    any_fragmented: bool
    map_ids: List[str]

    max_gap_minutes: float
    covered_seconds: float
    coverage_fraction: Optional[float]

    coverage_intervals: List[CoverageInterval]

    @property
    def coverage_percent(self) -> Optional[float]:
        if self.coverage_fraction is None:
            return None
        return self.coverage_fraction * 100.0


@dataclass
class AggregatedStats:
    count_replays: int
    count_failed: int
    count_skipped: int

    coverage_fractions: List[float]
    total_game_seconds_list: List[float]
    total_patches_list: List[int]

    mean_coverage: Optional[float]
    median_coverage: Optional[float]
    min_coverage: Optional[float]
    max_coverage: Optional[float]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute coverage and metadata statistics for a folder of ConflictInterface replay files.\n\n"
            "Coverage is defined as the fraction of the game duration where consecutive patches\n"
            "are never more than the configured max gap apart."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "replay_dir",
        type=Path,
        help="Directory containing replay files.",
    )
    parser.add_argument(
        "--pattern",
        default="*",
        help="Glob pattern to select replay files within the directory.",
    )
    parser.add_argument(
        "--max-gap-minutes",
        type=float,
        default=20.0,
        help="Maximum allowed gap between consecutive patches to consider an interval covered.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write graphs and optional JSON summary. Defaults to replay_dir.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional path to write a JSON summary with per-replay and aggregated statistics.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of replay files to process from the directory.",
    )
    parser.add_argument(
        "--no-graphs",
        action="store_true",
        help="Disable graph generation even if matplotlib is available.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=None,
        metavar="N",
        help="Number of worker processes. Default: use CPU count. Use 1 for sequential.",
    )

    return parser.parse_args(argv)


def discover_replay_files(replay_dir: Path, pattern: str, limit: Optional[int]) -> List[Path]:
    if not replay_dir.is_dir():
        raise ValueError(f"Replay directory does not exist or is not a directory: {replay_dir}")

    files = sorted(p for p in replay_dir.glob(pattern) if p.is_file())
    if limit is not None:
        files = files[:limit]
    return files


def _compute_coverage_intervals(
    timestamps: Sequence[datetime],
    max_gap_seconds: float,
) -> List[Tuple[datetime, datetime]]:
    """
    Build maximal contiguous intervals where consecutive patch timestamps are at most max_gap_seconds apart.

    Coverage definition: a span of time is "covered" if it lies between a first and last patch in a run
    where every adjacent pair of patches is within max_gap_seconds. So we group sorted timestamps into
    runs (breaking when gap > max_gap), then each run becomes one interval [first_ts, last_ts].
    Single-patch runs yield zero duration (interval [t, t]).
    """
    if not timestamps:
        return []

    intervals: List[Tuple[datetime, datetime]] = []
    start = prev = timestamps[0]

    for t in timestamps[1:]:
        gap = (t - prev).total_seconds()
        if gap <= max_gap_seconds:
            prev = t
            continue
        intervals.append((start, prev))
        start = prev = t

    intervals.append((start, prev))
    return intervals


def _clamp_intervals_to_game(
    intervals: Iterable[Tuple[datetime, datetime]],
    game_start: Optional[datetime],
    game_end: Optional[datetime],
) -> List[CoverageInterval]:
    result: List[CoverageInterval] = []
    for start, end in intervals:
        s = start
        e = end
        if game_start is not None and s < game_start:
            s = game_start
        if game_end is not None and e > game_end:
            e = game_end
        if e <= s:
            continue
        duration = (e - s).total_seconds()
        result.append(CoverageInterval(start=s, end=e, duration_seconds=duration))
    return result


def _worker(args: Tuple[Path, float]) -> Tuple[Path, Optional[ReplayStats], Optional[str]]:
    """Worker for multiprocessing: returns (path, stats, error). stats is None for skip or failure."""
    path, max_gap_minutes = args
    try:
        stats = load_replay_stats(path, max_gap_minutes)
        return (path, stats, None)
    except Exception as e:
        return (path, None, str(e))


def load_replay_stats(path: Path, max_gap_minutes: float) -> Optional[ReplayStats]:
    max_gap_seconds = max_gap_minutes * 60.0

    timeline = ReplayTimeline(path, mode="r")
    timeline.open()

    try:
        try:
            timeline_metadata = timeline.get_timeline_metadata()
        except Exception:
            timeline_metadata = None

        if timeline_metadata is not None and not timeline_metadata.game_ended:
            return None

        if timeline_metadata is not None:
            game_start = (
                datetime.fromtimestamp(timeline_metadata.start_of_game, tz=UTC)
                if timeline_metadata.start_of_game > 0
                else None
            )
            game_end = (
                datetime.fromtimestamp(timeline_metadata.end_of_game, tz=UTC)
                if timeline_metadata.end_of_game > 0
                else None
            )
            game_id = timeline_metadata.game_id or None
            player_id = timeline_metadata.player_id or None
            scenario_id = timeline_metadata.scenario_id or None
            day_of_game = timeline_metadata.day_of_game or None
            speed = timeline_metadata.speed or None
            segment_count = timeline_metadata.segment_count
            game_ended = timeline_metadata.game_ended
        else:
            game_start = None
            game_end = None
            game_id = None
            player_id = None
            scenario_id = None
            day_of_game = None
            speed = None
            segment_count = None
            game_ended = None

        if game_start is None or game_end is None:
            try:
                game_start = timeline.get_start_time()
                game_end = timeline.get_last_time()
            except Exception:
                game_start = None
                game_end = None

        total_game_seconds = 0.0
        if game_start is not None and game_end is not None:
            total_game_seconds = max(0.0, (game_end - game_start).total_seconds())

        segments_meta = timeline.get_segments_metadata()
        total_patches = 0
        any_fragmented = False
        map_ids_set = set()
        for meta in segments_meta.values():
            total_patches += int(meta.current_patches)
            any_fragmented = any_fragmented or bool(meta.is_fragmented)
            if getattr(meta, "map_id", ""):
                map_ids_set.add(meta.map_id)

        timestamps = timeline.get_timestamp_cache()
        if timestamps:
            first_patch_time = timestamps[0]
            last_patch_time = timestamps[-1]
            patch_span_seconds = max(0.0, (last_patch_time - first_patch_time).total_seconds())
        else:
            first_patch_time = None
            last_patch_time = None
            patch_span_seconds = 0.0

        raw_intervals = _compute_coverage_intervals(timestamps, max_gap_seconds=max_gap_seconds)
        coverage_intervals = _clamp_intervals_to_game(raw_intervals, game_start, game_end)
        covered_seconds = sum(iv.duration_seconds for iv in coverage_intervals)

        # If metadata game window is wrong: zero coverage despite patches, or unreasonably large total
        # (e.g. >14 days), use actual patch span so coverage is meaningful.
        MAX_REASONABLE_GAME_SECONDS = 14 * 24 * 3600  # 14 days
        if patch_span_seconds > 0.0 and first_patch_time is not None and last_patch_time is not None and (
            covered_seconds == 0.0 or total_game_seconds > MAX_REASONABLE_GAME_SECONDS
        ):
            game_start = first_patch_time
            game_end = last_patch_time
            total_game_seconds = patch_span_seconds
            coverage_intervals = _clamp_intervals_to_game(raw_intervals, game_start, game_end)
            covered_seconds = sum(iv.duration_seconds for iv in coverage_intervals)

        if total_game_seconds > 0.0:
            coverage_fraction: Optional[float] = covered_seconds / total_game_seconds
        else:
            coverage_fraction = None

        return ReplayStats(
            file_path=path,
            game_id=game_id,
            player_id=player_id,
            scenario_id=scenario_id,
            day_of_game=day_of_game,
            speed=speed,
            segment_count=segment_count,
            game_ended=game_ended,
            game_start=game_start,
            game_end=game_end,
            total_game_seconds=total_game_seconds,
            first_patch_time=first_patch_time,
            last_patch_time=last_patch_time,
            patch_span_seconds=patch_span_seconds,
            total_patches=total_patches,
            any_fragmented=any_fragmented,
            map_ids=sorted(map_ids_set),
            max_gap_minutes=max_gap_minutes,
            covered_seconds=covered_seconds,
            coverage_fraction=coverage_fraction,
            coverage_intervals=coverage_intervals,
        )
    finally:
        timeline.close()


def aggregate_stats(stats_list: Sequence[ReplayStats], failed_count: int, skipped_count: int = 0) -> AggregatedStats:
    covs = [s.coverage_fraction for s in stats_list if s.coverage_fraction is not None]
    game_durations = [s.total_game_seconds for s in stats_list]
    patch_counts = [s.total_patches for s in stats_list]

    if covs:
        mean_cov = mean(covs)
        median_cov = median(covs)
        min_cov = min(covs)
        max_cov = max(covs)
    else:
        mean_cov = median_cov = min_cov = max_cov = None

    return AggregatedStats(
        count_replays=len(stats_list),
        count_failed=failed_count,
        count_skipped=skipped_count,
        coverage_fractions=list(covs),
        total_game_seconds_list=game_durations,
        total_patches_list=patch_counts,
        mean_coverage=mean_cov,
        median_coverage=median_cov,
        min_coverage=min_cov,
        max_coverage=max_cov,
    )


def _serialize_replay_stats_for_json(stats: ReplayStats) -> dict:
    def dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt is not None else None

    base = asdict(stats)
    base["file_path"] = str(stats.file_path)
    base["game_start"] = dt_to_iso(stats.game_start)
    base["game_end"] = dt_to_iso(stats.game_end)
    base["first_patch_time"] = dt_to_iso(stats.first_patch_time)
    base["last_patch_time"] = dt_to_iso(stats.last_patch_time)
    base["coverage_percent"] = stats.coverage_percent

    base["coverage_intervals"] = [
        {
            "start": dt_to_iso(iv.start),
            "end": dt_to_iso(iv.end),
            "duration_seconds": iv.duration_seconds,
        }
        for iv in stats.coverage_intervals
    ]
    return base


def _serialize_agg_stats_for_json(agg: AggregatedStats) -> dict:
    return asdict(agg)


def render_graphs(stats_list: Sequence[ReplayStats], output_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore[import]
    except Exception:  # pragma: no cover - optional dependency
        logger.warning("matplotlib is not available; skipping graph generation")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    cov_values = []
    labels = []
    for s in stats_list:
        if s.coverage_fraction is None:
            continue
        cov_values.append(s.coverage_percent)
        labels.append(s.file_path.name)

    if cov_values:
        sorted_pairs = sorted(zip(labels, cov_values), key=lambda x: x[1] if x[1] is not None else 0.0)
        labels_sorted = [p[0] for p in sorted_pairs]
        cov_sorted = [p[1] for p in sorted_pairs]

        plt.figure(figsize=(max(6, len(cov_sorted) * 0.4), 4))
        plt.bar(range(len(cov_sorted)), cov_sorted)
        plt.xticks(range(len(cov_sorted)), labels_sorted, rotation=90)
        plt.ylabel("Coverage %")
        plt.title("Coverage per replay")
        plt.tight_layout()
        plt.savefig(output_dir / "coverage_per_replay.png")
        plt.close()

        plt.figure(figsize=(6, 4))
        plt.hist(cov_sorted, bins=20, edgecolor="black")
        plt.xlabel("Coverage %")
        plt.ylabel("Number of replays")
        plt.title("Coverage distribution")
        plt.tight_layout()
        plt.savefig(output_dir / "coverage_histogram.png")
        plt.close()


def print_console_summary(stats_list: Sequence[ReplayStats], agg: AggregatedStats) -> None:
    for s in stats_list:
        cov_str = "n/a"
        if s.coverage_percent is not None:
            cov_str = f"{s.coverage_percent:.1f}%"

        covered_hms = _format_seconds_hms(s.covered_seconds)
        total_hms = _format_seconds_hms(s.total_game_seconds)

        meta_bits = []
        if s.game_id is not None:
            meta_bits.append(f"game_id={s.game_id}")
        if s.scenario_id is not None:
            meta_bits.append(f"scenario={s.scenario_id}")
        if s.speed is not None:
            meta_bits.append(f"speed={s.speed}")

        meta_str = " ".join(meta_bits)
        print(
            f"{s.file_path.name}: {meta_str} coverage={cov_str} "
            f"(covered {covered_hms} / total {total_hms}, "
            f"patches={s.total_patches}, segments={s.segment_count or 0})"
        )

    print()
    print(f"Processed {agg.count_replays} replay(s); {agg.count_failed} file(s) failed to parse; {agg.count_skipped} skipped (game not ended).")

    if agg.mean_coverage is not None:
        print(
            "Coverage stats over valid replays: "
            f"mean={agg.mean_coverage*100:.1f}% "
            f"median={agg.median_coverage*100:.1f}% "
            f"min={agg.min_coverage*100:.1f}% "
            f"max={agg.max_coverage*100:.1f}%"
        )


def _format_seconds_hms(seconds: float) -> str:
    total = int(round(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    replay_dir: Path = args.replay_dir
    output_dir: Path = args.output_dir or replay_dir

    try:
        files = discover_replay_files(replay_dir, args.pattern, args.limit)
    except Exception as exc:
        logger.error("Failed to discover replay files: %s", exc)
        return 1

    if not files:
        logger.warning("No replay files found in %s with pattern %r", replay_dir, args.pattern)
        return 0

    stats_list: List[ReplayStats] = []
    failed = 0
    skipped = 0

    n_jobs = args.jobs if args.jobs is not None else max(1, (os.cpu_count() or 1))

    if n_jobs <= 1:
        if tqdm is not None:
            file_iter = tqdm(files, total=len(files), desc="Replays", unit="file")
        else:
            file_iter = files
        for path in file_iter:
            try:
                stats = load_replay_stats(path, args.max_gap_minutes)
                if stats is None:
                    skipped += 1
                    continue
                stats_list.append(stats)
            except Exception as exc:
                failed += 1
                logger.error("Failed to process replay %s: %s", path, exc)
    else:
        task_args = [(p, args.max_gap_minutes) for p in files]
        with multiprocessing.Pool(n_jobs) as pool:
            if tqdm is not None:
                result_iter = tqdm(
                    pool.imap_unordered(_worker, task_args, chunksize=1),
                    total=len(task_args),
                    desc="Replays",
                    unit="file",
                )
            else:
                result_iter = pool.imap_unordered(_worker, task_args, chunksize=1)
            for path, stats, error in result_iter:
                if error is not None:
                    failed += 1
                    logger.error("Failed to process replay %s: %s", path, error)
                elif stats is None:
                    skipped += 1
                else:
                    stats_list.append(stats)

    stats_list.sort(key=lambda s: s.file_path)
    agg = aggregate_stats(stats_list, failed, skipped)
    print_console_summary(stats_list, agg)

    if args.summary_json is not None:
        summary = {
            "config": {
                "replay_dir": str(replay_dir),
                "pattern": args.pattern,
                "max_gap_minutes": args.max_gap_minutes,
            },
            "replays": [_serialize_replay_stats_for_json(s) for s in stats_list],
            "aggregated": _serialize_agg_stats_for_json(agg),
        }
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        with args.summary_json.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, sort_keys=True)

    if not args.no_graphs:
        render_graphs(stats_list, output_dir=output_dir)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

