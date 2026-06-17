#!/usr/bin/env python3
"""
One-off generator for `tools/ml/src/ml/data/unit_vocab.json`.

Scans the unit-type registry (`mod_state.unit_types`) of a sample replay and
collects every distinct `unit_name`, sorted for determinism. This vocabulary
defines the per-unit-type loss slice of the per-player newspaper feature vector
(see `newspaper_features.py`) — its order and length must stay stable across
dataset extraction and training.

Usage:
    python tools/ml/scripts/build_unit_vocab.py \\
        --replay data/prod_replays/game_10808482_player_0.conrp \\
        --maps-dir data/maps_dir \\
        --output tools/ml/src/ml/data/unit_vocab.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from conflict_interface.interface.replay_interface import ReplayInterface


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", required=True, type=Path, help="Sample .conrp replay file")
    parser.add_argument("--maps-dir", required=True, type=Path, help="Directory of static map .bin files")
    parser.add_argument("--output", required=True, type=Path, help="Output unit_vocab.json path")
    args = parser.parse_args()

    static_map_data = {p.stem: p for p in args.maps_dir.glob("*.bin")}

    ritf = ReplayInterface(args.replay, static_map_data=static_map_data)
    if not ritf.open():
        raise SystemExit("replay.open() returned False")
    ritf.jump_to(ritf.start_time)
    gs = ritf.game_state
    if gs is None:
        raise SystemExit("game_state is None after jump_to(start_time)")

    unit_types = dict(gs.states.mod_state.unit_types)
    vocab = sorted({ut.unit_name for ut in unit_types.values() if ut.unit_name})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(vocab, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(vocab)} unit types to {args.output}")


if __name__ == "__main__":
    main()
