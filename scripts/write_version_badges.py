#!/usr/bin/env python
"""
Writes the shields.io endpoint JSON files backing the client-version badges in
the root README.

Two badges are produced:

  supported-client.json  the client version conflict_interface can parse
                         (data_types/newest/version.py)
  latest-client.json     the newest client version Conflict of Nations has
                         published, as detected by scripts/check_new_version.py

The colour of the "latest" badge encodes drift: green when the two match,
orange when Conlyse is behind the live game.

The files are published on the orphan `badges` branch rather than committed to
main, which is pull-request-only; the README reads them from there via
raw.githubusercontent.com. Output is byte-stable, so re-running with unchanged
inputs produces identical bytes and the workflow's comparison guard skips the
push.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / "libs/conflict_interface/conflict_interface/data_types/newest/version.py"

SUPPORTED_BADGE = "supported-client.json"
LATEST_BADGE = "latest-client.json"

SUPPORTED_COLOR = "blue"
IN_SYNC_COLOR = "brightgreen"
BEHIND_COLOR = "orange"
UNKNOWN_COLOR = "lightgrey"


def supported_version() -> int:
    """The version conflict_interface currently ships datatypes for."""
    try:
        from conflict_interface.versions import LATEST_VERSION

        return int(LATEST_VERSION)
    except ImportError:
        # conflict_interface is not installed (plain checkout) — read the constant directly.
        match = re.search(r"VERSION\s*=\s*(\d+)", VERSION_FILE.read_text())
        if not match:
            raise RuntimeError(f"Could not read VERSION from {VERSION_FILE}") from None
        return int(match.group(1))


def previous_client_version(out_dir: Path) -> int | None:
    """The client version recorded in an existing latest-client.json, if any."""
    path = out_dir / LATEST_BADGE
    if not path.is_file():
        return None
    message = json.loads(path.read_text()).get("message", "")
    match = re.fullmatch(r"v(\d+)", message)
    return int(match.group(1)) if match else None


def latest_color(client: int, supported: int) -> str:
    if client == supported:
        return IN_SYNC_COLOR
    if client > supported:
        return BEHIND_COLOR
    # The live client is older than what we support — unexpected, but not worth failing over.
    return UNKNOWN_COLOR


def badge(label: str, version: int, color: str) -> dict:
    return {"schemaVersion": 1, "label": label, "message": f"v{version}", "color": color}


def write_badge(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-version",
        type=int,
        help="Newest client version published by Conflict of Nations "
        "(default: keep the value already in latest-client.json)",
    )
    parser.add_argument(
        "--supported-version",
        type=int,
        help="Client version conflict_interface supports (default: read from the library)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory to write the badge JSON into. Deliberately has no default: the "
        "badges live on the `badges` branch, not in this checkout.",
    )
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    supported = (
        args.supported_version if args.supported_version is not None else supported_version()
    )

    client = args.client_version
    if client is None:
        client = previous_client_version(out_dir)
    if client is None:
        parser.error(
            f"--client-version is required when {out_dir / LATEST_BADGE} does not exist yet"
        )

    write_badge(out_dir / SUPPORTED_BADGE, badge("supported client", supported, SUPPORTED_COLOR))
    write_badge(
        out_dir / LATEST_BADGE,
        badge("latest CoN client", client, latest_color(client, supported)),
    )

    print(f"supported client=v{supported} latest CoN client=v{client}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
