#!/usr/bin/env python3
"""
One-off generator for `tools/ml/src/ml/data/building_vocab.json`.

Scans the upgrade-type registry (`mod_state.upgrades`) of a sample replay and
collects every player-constructable building type as `"{identifier}_t{tier}"`,
sorted for determinism. This vocabulary defines the `building_counts` slice of the
per-province feature vector (see `province_features.py`) — its order and length
must stay stable across dataset extraction and training.

Usage:
    python tools/ml/scripts/build_building_vocab.py \\
        --replay replays_out/game_10626204.conrp \\
        --maps-dir maps_dir \\
        --output tools/ml/src/ml/data/building_vocab.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from conflict_interface.interface.replay_interface import ReplayInterface

# Upgrades that have resource costs but aren't persistent buildings (one-time actions).
_NON_BUILDING_NAMES = frozenset({"Annex City", "Relocate Headquarters", "Nationalize"})


def _is_player_building(upgrade_type) -> bool:
    if upgrade_type.upgrade_name in _NON_BUILDING_NAMES:
        return False
    return bool(upgrade_type.costs)


def _building_key(upgrade_type) -> str:
    identifier = upgrade_type.upgrade_identifier or upgrade_type.upgrade_name or str(upgrade_type.id)
    identifier = identifier.replace(" ", "_").replace("-", "_")
    return f"{identifier}_t{upgrade_type.tier}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", required=True, type=Path, help="Sample .conrp replay file")
    parser.add_argument("--maps-dir", required=True, type=Path, help="Directory of static map .bin files")
    parser.add_argument("--output", required=True, type=Path, help="Output building_vocab.json path")
    args = parser.parse_args()

    static_map_data = {p.stem: p for p in args.maps_dir.glob("*.bin")}

    ritf = ReplayInterface(args.replay, static_map_data=static_map_data)
    if not ritf.open():
        raise SystemExit("replay.open() returned False")
    ritf.jump_to(ritf.start_time)
    gs = ritf.game_state
    if gs is None:
        raise SystemExit("game_state is None after jump_to(start_time)")

    ut_map = dict(gs.states.mod_state.upgrades)

    vocab = sorted({_building_key(ut) for ut in ut_map.values() if _is_player_building(ut)})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(vocab, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(vocab)} building types to {args.output}")


if __name__ == "__main__":
    main()
