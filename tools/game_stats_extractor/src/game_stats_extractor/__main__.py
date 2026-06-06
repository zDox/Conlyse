"""CLI entry point for game-stats-extractor."""
import argparse
import logging
import os
import sys
from pathlib import Path


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show ERROR messages")


def _configure_logging(args: argparse.Namespace) -> None:
    level = logging.DEBUG if args.verbose else (logging.ERROR if args.quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _cmd_stats(args: argparse.Namespace) -> None:
    if not args.replays_dir.is_dir():
        print(f"Error: replays-dir does not exist: {args.replays_dir}", file=sys.stderr)
        sys.exit(1)
    if args.map_data_dir and not args.map_data_dir.is_dir():
        print(f"Error: map-data-dir does not exist: {args.map_data_dir}", file=sys.stderr)
        sys.exit(1)

    from .pipeline import Pipeline

    Pipeline(
        replays_dir=args.replays_dir,
        output_dir=args.output,
        workers=args.workers,
        map_data_dir=args.map_data_dir,
        min_province_appearances=args.min_province_appearances,
        min_timeseries_games=args.min_timeseries_games,
    ).run()


def _cmd_ml_dataset(args: argparse.Namespace) -> None:
    if not args.replays_dir.is_dir():
        print(f"Error: replays-dir does not exist: {args.replays_dir}", file=sys.stderr)
        sys.exit(1)
    if args.map_data_dir and not args.map_data_dir.is_dir():
        print(f"Error: map-data-dir does not exist: {args.map_data_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        import pandas as pd
    except ImportError:
        print(
            "Error: pandas is required for ml-dataset. "
            'Install with: pip install "game-stats-extractor[parquet]"',
            file=sys.stderr,
        )
        sys.exit(1)

    from concurrent.futures import ProcessPoolExecutor, as_completed

    from tqdm import tqdm

    from .models.training import training_rows_from_game_data
    from .pipeline import _extract_worker

    replay_files = sorted(args.replays_dir.glob("game_*.conrp"))
    if not replay_files:
        print(f"Error: no game_*.conrp files found in {args.replays_dir}", file=sys.stderr)
        sys.exit(1)

    logger = logging.getLogger(__name__)
    logger.info("Found %d replay files", len(replay_files))

    worker_args = [(f, args.map_data_dir) for f in replay_files]
    all_rows = []
    failed = 0

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(_extract_worker, a): a[0] for a in worker_args}
            for future in tqdm(as_completed(futures), total=len(futures), desc="Extracting"):
                game = future.result()
                if game is None:
                    failed += 1
                else:
                    all_rows.extend(
                        training_rows_from_game_data(game, min_coverage=args.min_bucket_coverage)
                    )
    else:
        from .extractors.replay_extractor import ReplayExtractor

        extractor = ReplayExtractor(map_data_dir=args.map_data_dir)
        for f in tqdm(replay_files, desc="Extracting"):
            game = extractor.extract_safe(f)
            if game is None:
                failed += 1
            else:
                all_rows.extend(
                    training_rows_from_game_data(game, min_coverage=args.min_bucket_coverage)
                )

    logger.info(
        "Collected %d training rows from %d games (%d failed)",
        len(all_rows),
        len(replay_files) - failed,
        failed,
    )

    if not all_rows:
        print("Error: no training rows produced", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([r.to_dict() for r in all_rows])
    df.to_parquet(args.output, index=False)
    logger.info("Written %d rows to %s", len(df), args.output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="game-stats-extractor — extract and aggregate CoN replay statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── stats ──────────────────────────────────────────────────────────────
    stats_p = sub.add_parser(
        "stats",
        help="Extract per-game statistics and aggregate to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  game-stats-extractor stats --replays-dir /path/to/replays --output ./stats
  game-stats-extractor stats --replays-dir replays_out --output ./stats --workers 4 -v
        """,
    )
    stats_p.add_argument("--replays-dir", required=True, type=Path,
                         help="Directory containing game_*.conrp replay files")
    stats_p.add_argument("--output", required=True, type=Path,
                         help="Output directory for JSON stat files")
    stats_p.add_argument("--map-data-dir", type=Path, default=None,
                         help="Directory containing static map .bin files (optional)")
    stats_p.add_argument("--workers", type=int, default=os.cpu_count() or 1,
                         help="Number of parallel worker processes (default: CPU count)")
    stats_p.add_argument("--min-province-appearances", type=int, default=3,
                         help="Min game appearances for province to appear in output (default: 3)")
    stats_p.add_argument("--min-timeseries-games", type=int, default=3,
                         help="Min games for country to appear in time series output (default: 3)")
    _add_common_args(stats_p)

    # ── ml-dataset ─────────────────────────────────────────────────────────
    ml_p = sub.add_parser(
        "ml-dataset",
        help="Build a Parquet training dataset for win-probability ML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  game-stats-extractor ml-dataset --replays-dir replays_out --output training.parquet
  game-stats-extractor ml-dataset --replays-dir replays_out --output training.parquet \\
      --workers 8 --min-bucket-coverage 2
        """,
    )
    ml_p.add_argument("--replays-dir", required=True, type=Path,
                      help="Directory containing game_*.conrp replay files")
    ml_p.add_argument("--output", required=True, type=Path,
                      help="Output Parquet file path (e.g. training.parquet)")
    ml_p.add_argument("--map-data-dir", type=Path, default=None,
                      help="Directory containing static map .bin files (optional)")
    ml_p.add_argument("--workers", type=int, default=os.cpu_count() or 1,
                      help="Number of parallel worker processes (default: CPU count)")
    ml_p.add_argument(
        "--min-bucket-coverage",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Minimum update ticks a 5%%-bucket must have to be included as a training row "
            "(default: 1; recommended: 2 to exclude single-tick boundary snapshots)"
        ),
    )
    _add_common_args(ml_p)

    args = parser.parse_args()
    _configure_logging(args)

    try:
        if args.command == "stats":
            _cmd_stats(args)
        elif args.command == "ml-dataset":
            _cmd_ml_dataset(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        logging.getLogger(__name__).exception("Command failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
