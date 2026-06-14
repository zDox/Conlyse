"""CLI entry point for gnn-extract."""
from __future__ import annotations

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


def _extract_one(args: tuple[Path, Path, Path, Path]) -> tuple[Path, bool, str]:
    replay_path, maps_dir, graph_cache_dir, output_dir = args
    import torch

    from .extractor import GnnReplayExtractor

    try:
        sample = GnnReplayExtractor(maps_dir, graph_cache_dir).extract(replay_path)
    except Exception as exc:  # noqa: BLE001 — reported back to the main process
        return replay_path, False, str(exc)

    output_path = output_dir / f"game_{sample['game_id']}.pt"
    torch.save(sample, output_path)
    return replay_path, True, ""


def _cmd_build(args: argparse.Namespace) -> None:
    if not args.replays_dir.is_dir():
        print(f"Error: replays-dir does not exist: {args.replays_dir}", file=sys.stderr)
        sys.exit(1)
    if not args.maps_dir.is_dir():
        print(f"Error: maps-dir does not exist: {args.maps_dir}", file=sys.stderr)
        sys.exit(1)

    from concurrent.futures import ProcessPoolExecutor, as_completed

    from tqdm import tqdm

    replay_files = sorted(args.replays_dir.glob("game_*.conrp"))
    if not replay_files:
        print(f"Error: no game_*.conrp files found in {args.replays_dir}", file=sys.stderr)
        sys.exit(1)

    logger = logging.getLogger(__name__)
    logger.info("Found %d replay files", len(replay_files))

    args.output.mkdir(parents=True, exist_ok=True)
    args.graph_cache_dir.mkdir(parents=True, exist_ok=True)

    worker_args = [(f, args.maps_dir, args.graph_cache_dir, args.output) for f in replay_files]
    failed: list[tuple[Path, str]] = []
    succeeded = 0

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(_extract_one, a): a[0] for a in worker_args}
            for future in tqdm(as_completed(futures), total=len(futures), desc="Extracting"):
                path, ok, error = future.result()
                if ok:
                    succeeded += 1
                else:
                    failed.append((path, error))
    else:
        for a in tqdm(worker_args, desc="Extracting"):
            path, ok, error = _extract_one(a)
            if ok:
                succeeded += 1
            else:
                failed.append((path, error))

    logger.info("Extracted %d/%d games (%d failed)", succeeded, len(replay_files), len(failed))
    for path, error in failed:
        logger.warning("Failed: %s — %s", path.name, error)

    if succeeded == 0:
        print("Error: no samples extracted", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="gnn-extract — build GNN win-predictor training samples from CoN replays",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    build_p = sub.add_parser(
        "build",
        help="Extract one .pt sample per finished replay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gnn-extract build --replays-dir replays_out --maps-dir maps_dir --output data/ml/gnn_dataset
  gnn-extract build --replays-dir replays_out --maps-dir maps_dir --output data/ml/gnn_dataset --workers 4
        """,
    )
    build_p.add_argument("--replays-dir", required=True, type=Path,
                          help="Directory containing game_*.conrp replay files")
    build_p.add_argument("--maps-dir", required=True, type=Path,
                          help="Directory containing static map .bin files")
    build_p.add_argument("--output", required=True, type=Path,
                          help="Output directory for game_<id>.pt sample files")
    build_p.add_argument("--graph-cache-dir", type=Path, default=Path("data/ml/graph_cache"),
                          help="Directory for cached province-graph .npz files (default: data/ml/graph_cache)")
    build_p.add_argument("--workers", type=int, default=os.cpu_count() or 1,
                          help="Number of parallel worker processes (default: CPU count)")
    _add_common_args(build_p)

    args = parser.parse_args()
    _configure_logging(args)

    try:
        if args.command == "build":
            _cmd_build(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        logging.getLogger(__name__).exception("Command failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
