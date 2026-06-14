"""
Extracts a single GNN win-predictor training sample from one finished `.conrp` replay.

For each game, builds a `T_STEPS`-snapshot sequence (3-day spacing, right-aligned to
"now" = the end of the replay) of per-province node features and per-player features,
plus the target win-coalition distribution. One sample == one `.pt` file.
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
from ml.data.resampling import T_STEPS, build_resampling_schedule
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
                raise ValueError("replay.open() returned False — file may be incomplete or corrupted")
            return self._extract(replay, file_path, meta)
        finally:
            replay.close()

    def _extract(self, replay: ReplayInterface, file_path: Path, meta) -> dict:
        start_time = replay.start_time
        last_time = replay.last_time
        day_of_game = (last_time - start_time).total_seconds() / 86400.0

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

        schedule = build_resampling_schedule(day_of_game)

        node_features = np.zeros((T_STEPS, num_nodes, NUM_PROVINCE_FEATURES), dtype=np.float32)
        owner_seat_idx = np.zeros((T_STEPS, num_nodes), dtype=np.int64)
        player_features = np.zeros((T_STEPS, num_players, NUM_PLAYER_FEATURES), dtype=np.float32)
        alive_mask = np.zeros((T_STEPS, num_players), dtype=bool)
        time_mask = np.zeros((T_STEPS,), dtype=bool)

        for step in schedule:
            time_mask[step.index] = step.valid
            if not step.valid:
                continue

            replay.jump_to(start_time + timedelta(days=step.target_day))
            gs = replay.game_state
            if gs is None:
                raise ValueError(f"game_state is None at resampling step {step.index}")

            provinces = gs.states.map_state.map.provinces
            ut_map = dict(gs.states.mod_state.upgrades)
            profiles = gs.states.player_state.players

            capital_province_ids = {p.capital_id for p in profiles.values() if p.capital_id and p.capital_id > 0}

            province_counts: dict[int, int] = {}
            for province in provinces.values():
                if isinstance(province, LandProvince) and province.owner_id > 0:
                    province_counts[province.owner_id] = province_counts.get(province.owner_id, 0) + 1

                node_idx = id_to_index.get(province.id)
                if node_idx is None:
                    continue
                node_features[step.index, node_idx] = build_province_feature_vector(
                    province, ut_map, capital_province_ids
                )
                owner_seat_idx[step.index, node_idx] = build_owner_seat_idx(province, seat_idx)

            for i, player_id in enumerate(player_ids):
                profile = profiles.get(player_id)
                if profile is None:
                    continue
                player_features[step.index, i] = build_player_feature_vector(
                    profile, province_counts.get(player_id, 0)
                )
                alive_mask[step.index, i] = not profile.defeated

        replay.jump_to(last_time)
        gs = replay.game_state
        if gs is None:
            raise ValueError("game_state is None at last_time")
        final_profiles = gs.states.player_state.players
        winner_ids = determine_winner_ids([final_profiles[pid] for pid in player_ids if pid in final_profiles])
        target = compute_target_vector(winner_ids, player_ids)

        game_id = meta.game_id or int(file_path.stem.replace("game_", ""))

        return {
            "game_id": game_id,
            "map_id": str(map_id),
            "node_ids": torch.from_numpy(graph.node_ids),
            "edge_index": torch.from_numpy(graph.edge_index),
            "node_features": torch.from_numpy(node_features),
            "owner_seat_idx": torch.from_numpy(owner_seat_idx),
            "player_features": torch.from_numpy(player_features),
            "alive_mask": torch.from_numpy(alive_mask),
            "time_mask": torch.from_numpy(time_mask),
            "target": torch.from_numpy(target),
            "player_ids": torch.tensor(player_ids, dtype=torch.long),
            "day_of_game": torch.tensor(day_of_game, dtype=torch.float32),
        }
