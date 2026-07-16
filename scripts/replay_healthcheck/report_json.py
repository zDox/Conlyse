"""Machine-readable JSON export.

Intended as the artifact a future automated filtering step (in
game_stats_extractor or gnn_extractor) could consume to exclude low-quality
replays from a corpus — no such integration is built here, only the export.
"""

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .aggregate import province_consistency
from .models import ReplayHealth


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _seconds(td: timedelta | None) -> float | None:
    return td.total_seconds() if td is not None else None


def _replay_to_dict(r: ReplayHealth) -> dict:
    return {
        "game_id": r.game_id,
        "player_id": r.player_id,
        "name": r.name,
        "status": r.status.value,
        "failure_category": r.failure_category.value if r.failure_category else None,
        "failure_detail": r.failure_detail,
        "parse_depth": r.parse_depth,
        "degraded_reasons": r.degraded_reasons,
        "segment_count": r.segment_count,
        "patches": r.patches,
        "map_id": r.map_id,
        "seg_first_ts": _iso(r.seg_first_ts),
        "seg_last_ts": _iso(r.seg_last_ts),
        "required_versions": sorted(r.required_versions),
        "unsupported_versions": sorted(r.unsupported_versions),
        "start_of_game": _iso(r.start_of_game),
        "end_of_game": _iso(r.end_of_game),
        "day_first": r.day_first,
        "day_last": r.day_last,
        "time_scale": r.time_scale,
        "game_ended": r.game_ended,
        "ranking_initialized": r.ranking_initialized,
        "province_count": len(r.province_ids) if r.province_ids is not None else None,
        "expected_province_count": len(r.expected_province_ids) if r.expected_province_ids is not None else None,
        "missing_province_ids": (
            sorted(r.expected_province_ids - r.province_ids)
            if r.expected_province_ids is not None and r.province_ids is not None
            else None
        ),
        "player_count": r.player_count,
        "real_player_count": r.real_player_count,
        "has_real_players": r.has_real_players,
        "invalid_activity_state_count": r.invalid_activity_state_count,
        "n_timestamps": r.n_timestamps,
        "typical_interval_seconds": _seconds(r.typical_interval),
        "gap_count": r.gap_count,
        "gap_total_seconds": _seconds(r.gap_total),
        "covered_seconds": r.covered_seconds,
    }


def write_json_report(results: list[ReplayHealth], output_path: Path, replays_dir: Path) -> None:
    status_counts = Counter(r.status.value for r in results)
    failure_counts = Counter(r.failure_category.value for r in results if r.failure_category)
    reason_counts: Counter = Counter()
    for r in results:
        reason_counts.update(r.degraded_reasons)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "replays_dir": str(replays_dir),
        "summary": {
            "total": len(results),
            "status_counts": dict(status_counts),
            "failure_category_counts": dict(failure_counts),
            "degraded_reason_counts": dict(reason_counts),
            "province_consistency": {
                map_id: {
                    "n_games": info["n_games"],
                    "expected_count": info["expected_count"],
                    "min_actual": min(info["counts"]),
                    "max_actual": max(info["counts"]),
                }
                for map_id, info in province_consistency(results).items()
            },
        },
        "replays": [_replay_to_dict(r) for r in results],
    }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Replay health JSON export written to {output_path}", flush=True)
