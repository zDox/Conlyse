"""
Extracts GNN win-predictor training samples from one finished `.conrp` replay.

Each replay yields `NUM_ANCHORS` samples anchored at deterministic, evenly-spaced
mid-game days (`build_anchor_days`) — never the game-ending state itself, which would
leak the outcome into the input since the target is derived from that same state.
Each anchor's input is a `T_STEPS`-snapshot sequence (1-day spacing, right-aligned to
the anchor day) of per-province node features and per-player features.

Snapshot extraction is deduplicated across the `NUM_ANCHORS` anchors of a game: the
union of distinct in-game days actually needed is computed up front and the replay is
walked once over that "snapshot pool". The pool's per-province features are then
delta-encoded across consecutive days (only changed provinces are stored after the
first day) since most provinces don't change day-to-day. One game == one `.pt` file;
`ml.data.dataset.GnnWinDataset` reconstructs and slices out each anchor's dense
`[T_STEPS, ...]` view at load time.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import numpy as np
import torch
from conflict_interface.data_types.newest.map_state.land_province import LandProvince
from conflict_interface.interface.replay_interface import ReplayInterface
from ml.data.player_features import NUM_PLAYER_FEATURES, build_player_feature_vector
from ml.data.province_features import (
    NUM_PROVINCE_FEATURES,
    build_owner_seat_idx,
    build_province_feature_vector,
)
from ml.data.province_graph import get_or_build_province_graph
from ml.data.resampling import NUM_ANCHORS, T_STEPS, build_anchor_days, build_resampling_schedule
from ml.data.target import compute_target_vector, determine_winner_ids

logger = logging.getLogger(__name__)


class GnnReplayExtractor:
    def __init__(self, maps_dir: Path, graph_cache_dir: Path):
        self.maps_dir = maps_dir
        self.graph_cache_dir = graph_cache_dir
        self._static_map_data = {p.stem: p for p in maps_dir.glob("*.bin")}

    def extract(self, file_path: Path) -> dict:
        meta_replay = ReplayInterface(file_path)
        try:
            if not meta_replay.open(mode="read_metadata"):
                raise ValueError("replay.open(read_metadata) returned False")
            meta = meta_replay.get_timeline_metadata()
        finally:
            meta_replay.close()

        if not meta.game_ended:
            raise ValueError("game has not ended yet (game_ended=False in timeline metadata)")

        replay = ReplayInterface(file_path, static_map_data=self._static_map_data)
        try:
            if not replay.open():
                raise ValueError(
                    "replay.open() returned False — file may be incomplete or corrupted"
                )
            return self._extract(replay, file_path, meta)
        finally:
            replay.close()

    def _extract(self, replay: ReplayInterface, file_path: Path, meta) -> dict:
        start_time = replay.start_time
        last_time = replay.last_time
        day_of_game_end = (last_time - start_time).total_seconds() / 86400.0

        replay.jump_to(start_time)
        gs = replay.game_state
        if gs is None:
            raise ValueError("game_state is None after jump_to(start_time)")

        map_id = gs.states.map_state.map.map_id
        if not map_id:
            raise ValueError("map_id missing from game state")

        graph = get_or_build_province_graph(str(map_id), self.maps_dir, self.graph_cache_dir)
        id_to_index = graph.id_to_index()
        num_nodes = graph.num_nodes

        players_map = gs.states.player_state.players
        player_ids = sorted(
            pid
            for pid, profile in players_map.items()
            if pid > 0 and profile.nation_name and profile.name != "Guest"
        )
        if not player_ids:
            raise ValueError("no real players found in game state")
        seat_idx = {pid: i + 1 for i, pid in enumerate(player_ids)}  # seat 0 = neutral
        num_players = len(player_ids)

        anchor_days = build_anchor_days(day_of_game_end)
        schedules = [build_resampling_schedule(float(anchor_day)) for anchor_day in anchor_days]

        needed_days = sorted(
            {int(step.target_day) for sched in schedules for step in sched if step.valid}
        )
        num_snapshots = len(needed_days)

        node_features_pool = np.zeros(
            (num_snapshots, num_nodes, NUM_PROVINCE_FEATURES), dtype=np.float32
        )
        owner_seat_idx_pool = np.zeros((num_snapshots, num_nodes), dtype=np.int64)
        player_features_pool = np.zeros(
            (num_snapshots, num_players, NUM_PLAYER_FEATURES), dtype=np.float32
        )
        alive_mask_pool = np.zeros((num_snapshots, num_players), dtype=bool)

        for pool_idx, day in enumerate(needed_days):
            replay.jump_to(start_time + timedelta(days=day))
            gs = replay.game_state
            if gs is None:
                raise ValueError(f"game_state is None at snapshot day {day}")

            provinces = gs.states.map_state.map.provinces
            ut_map = dict(gs.states.mod_state.upgrades)
            profiles = gs.states.player_state.players

            capital_province_ids = {
                p.capital_id for p in profiles.values() if p.capital_id and p.capital_id > 0
            }

            province_counts: dict[int, int] = {}
            for province in provinces.values():
                if isinstance(province, LandProvince) and province.owner_id > 0:
                    province_counts[province.owner_id] = (
                        province_counts.get(province.owner_id, 0) + 1
                    )

                node_idx = id_to_index.get(province.id)
                if node_idx is None:
                    continue
                node_features_pool[pool_idx, node_idx] = build_province_feature_vector(
                    province, ut_map, capital_province_ids
                )
                owner_seat_idx_pool[pool_idx, node_idx] = build_owner_seat_idx(province, seat_idx)

            for i, player_id in enumerate(player_ids):
                profile = profiles.get(player_id)
                if profile is None:
                    continue
                player_features_pool[pool_idx, i] = build_player_feature_vector(
                    profile, province_counts.get(player_id, 0)
                )
                alive_mask_pool[pool_idx, i] = not profile.defeated

        replay.jump_to(last_time)
        gs = replay.game_state
        if gs is None:
            raise ValueError("game_state is None at last_time")
        final_profiles = gs.states.player_state.players
        winner_ids = determine_winner_ids(
            [final_profiles[pid] for pid in player_ids if pid in final_profiles]
        )
        target = compute_target_vector(winner_ids, player_ids)

        # Delta-encode the per-province pool: day 0 in full, later days store only
        # the provinces whose features or owner changed since the previous day.
        node_features_delta_idx: list[torch.Tensor] = []
        node_features_delta_val: list[torch.Tensor] = []
        owner_seat_idx_delta_val: list[torch.Tensor] = []
        for k in range(1, num_snapshots):
            changed = np.any(node_features_pool[k] != node_features_pool[k - 1], axis=-1)
            changed |= owner_seat_idx_pool[k] != owner_seat_idx_pool[k - 1]
            idx = np.flatnonzero(changed)
            node_features_delta_idx.append(torch.from_numpy(idx.astype(np.int64)))
            node_features_delta_val.append(torch.from_numpy(node_features_pool[k, idx]))
            owner_seat_idx_delta_val.append(torch.from_numpy(owner_seat_idx_pool[k, idx]))

        # Map each anchor's resampling steps onto the shared snapshot pool.
        day_to_pool_idx = {day: i for i, day in enumerate(needed_days)}
        step_to_pool_idx = np.full((NUM_ANCHORS, T_STEPS), -1, dtype=np.int64)
        time_mask = np.zeros((NUM_ANCHORS, T_STEPS), dtype=bool)
        for anchor_idx, sched in enumerate(schedules):
            for step in sched:
                time_mask[anchor_idx, step.index] = step.valid
                if step.valid:
                    step_to_pool_idx[anchor_idx, step.index] = day_to_pool_idx[int(step.target_day)]

        game_id = meta.game_id or int(file_path.stem.replace("game_", ""))

        return {
            "game_id": game_id,
            "map_id": str(map_id),
            "node_ids": torch.from_numpy(graph.node_ids),
            "edge_index": torch.from_numpy(graph.edge_index),
            "player_ids": torch.tensor(player_ids, dtype=torch.long),
            "target": torch.from_numpy(target),
            "snapshot_days": torch.tensor(needed_days, dtype=torch.float32),
            "node_features_first": torch.from_numpy(node_features_pool[0]),
            "owner_seat_idx_first": torch.from_numpy(owner_seat_idx_pool[0]),
            "node_features_delta_idx": node_features_delta_idx,
            "node_features_delta_val": node_features_delta_val,
            "owner_seat_idx_delta_val": owner_seat_idx_delta_val,
            "player_features": torch.from_numpy(player_features_pool),
            "alive_mask": torch.from_numpy(alive_mask_pool),
            "anchor_day_of_game": torch.tensor(anchor_days, dtype=torch.float32),
            "step_to_pool_idx": torch.from_numpy(step_to_pool_idx),
            "time_mask": torch.from_numpy(time_mask),
        }
