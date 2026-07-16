"""
Replay health check — analyzes a local folder of replay files.

  python scripts/replay_healthcheck/__main__.py --replays-dir data/prod_replays

What it does:
  1. Discovers game_<id>_player_<id>.conrp files in --replays-dir (assumed to
     already be in the current v3 container format — no auto-migration)
  2. Runs a staged analysis per replay: file existence, metadata, datatype
     version compatibility, structural integrity, then (if static map data
     is available) a full parse for game-content quality — classifying each
     replay as OK / DEGRADED / FAILED with a specific reason
  3. Prints a detailed terminal report
  4. Writes replay_health_report.html (charts) and replay_health.json
     (machine-readable export) to --output-dir

Dependencies (pip install if missing):
  tqdm  matplotlib  numpy  conflict_interface (or repo on PYTHONPATH)

Optional:
  --map-data-dir points at a directory of static map .bin files (default:
  data/maps_dir). Without static map data for a given replay's map_id, that
  replay only reaches "metadata_only" depth — file-integrity and version
  checks still run, but game-content quality checks (ranking, provinces,
  coverage, players) are skipped rather than misreported.
"""

import argparse
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _THIS_DIR.parent
REPO_ROOT = _SCRIPTS_DIR.parent

sys.path.insert(0, str(REPO_ROOT / "libs" / "conflict_interface"))
sys.path.insert(0, str(_SCRIPTS_DIR))

from replay_healthcheck.analyze import analyze_replays  # noqa: E402
from replay_healthcheck.discovery import discover_replays  # noqa: E402
from replay_healthcheck.report_html import generate_health_report  # noqa: E402
from replay_healthcheck.report_json import write_json_report  # noqa: E402
from replay_healthcheck.report_text import print_report  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay health check — analyzes a local folder of replays and reports coverage/quality metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--replays-dir", required=True, type=Path,
        help="Directory containing game_<id>_player_<id>.conrp replay files",
    )
    parser.add_argument(
        "--map-data-dir", type=Path, default=REPO_ROOT / "data" / "maps_dir",
        help="Directory containing static map .bin files (default: data/maps_dir)",
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help="Number of worker processes for replay parsing (default: CPU count)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path.cwd(),
        help="Directory to write replay_health_report.html and replay_health.json (default: current directory)",
    )
    args = parser.parse_args()

    if not args.replays_dir.is_dir():
        sys.exit(f"ERROR: replays-dir does not exist: {args.replays_dir}")

    rows = discover_replays(args.replays_dir)
    if not rows:
        print("No replay files found — nothing to analyse.")
        sys.exit(0)

    static_map_data: dict = {}
    if args.map_data_dir and args.map_data_dir.exists():
        static_map_data = {p.stem: p for p in args.map_data_dir.glob("*.bin")}
    else:
        print(
            f"  Note: {args.map_data_dir} not found — replays will only reach "
            f"metadata_only depth (file-integrity/version checks only)",
            flush=True,
        )

    import os
    workers = args.workers or os.cpu_count() or 1

    print(f"\nAnalysing {len(rows)} replays ...", flush=True)
    results = analyze_replays(rows, static_map_data=static_map_data, workers=workers)

    print_report(results)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    generate_health_report(results, args.output_dir / "replay_health_report.html")
    write_json_report(results, args.output_dir / "replay_health.json", args.replays_dir)


if __name__ == "__main__":
    main()
