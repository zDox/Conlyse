"""
Live win-share prediction for the Desktop replay viewer.

Maintains a rolling buffer of resampled (1-day spaced) game-state snapshots for one
replay session and builds GNN win-predictor inputs from it, reusing
`ml.data.{province_features,player_features}` — the exact same feature-building code
path as `gnn-extract` — so there is no train/serve skew.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import torch
from conflict_interface.data_types.newest.map_state.land_province import LandProvince
from ml.data.dataset import GnnBatch, collate_fn
from ml.data.player_features import NUM_PLAYER_FEATURES, build_player_feature_vector
from ml.data.province_features import (
    NUM_PROVINCE_FEATURES,
    build_owner_seat_idx,
    build_province_feature_vector,
)
from ml.data.province_graph import ProvinceGraph
from ml.data.resampling import STEP_DAYS, T_STEPS

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface

logger = logging.getLogger(__name__)


def _real_player_ids(players: dict) -> list[int]:
    return sorted(
        pid
        for pid, profile in players.items()
        if pid > 0 and profile.nation_name and profile.name != "Guest"
    )


class WinPredictionSession:
    """Rolling buffer of up to `T_STEPS` (1-day spaced) snapshots for one replay session."""

    def __init__(self, province_graph: ProvinceGraph, max_steps: int = T_STEPS) -> None:
        self.province_graph = province_graph
        self.max_steps = max_steps
        self.id_to_index = province_graph.id_to_index()
        self.edge_index = torch.from_numpy(province_graph.edge_index)

        self.player_ids: list[int] = []
        self.seat_idx: dict[int, int] = {}
        self._snapshots: list[dict] = []
        self._days: list[float] = []

    def maybe_update(self, ritf: ReplayInterface) -> bool:
        """Capture a new snapshot if `current_time` crossed the next `STEP_DAYS`
        boundary (or this is the first call). Returns True if the buffer changed."""
        game_state = ritf.game_state
        if game_state is None:
            return False

        day = (ritf.current_time - ritf.start_time).total_seconds() / 86400.0

        if self._days and day < self._days[-1] - STEP_DAYS / 2:
            # Replay scrubbed backwards far enough to invalidate the buffer.
            self._snapshots.clear()
            self._days.clear()

        if self._days and (day - self._days[-1]) < STEP_DAYS:
            return False

        snapshot = self._capture(game_state)
        if snapshot is None:
            return False

        self._snapshots.append(snapshot)
        self._days.append(day)
        if len(self._snapshots) > self.max_steps:
            self._snapshots.pop(0)
            self._days.pop(0)
        return True

    def _capture(self, game_state) -> dict | None:
        players = game_state.states.player_state.players
        if not self.player_ids:
            self.player_ids = _real_player_ids(players)
            self.seat_idx = {pid: i + 1 for i, pid in enumerate(self.player_ids)}
        if not self.player_ids:
            return None

        ut_map = dict(game_state.states.mod_state.upgrades)
        capital_province_ids = {
            profile.capital_id
            for profile in players.values()
            if profile.capital_id and profile.capital_id > 0
        }

        provinces = game_state.states.map_state.map.provinces
        num_nodes = self.province_graph.num_nodes
        node_features = np.zeros((num_nodes, NUM_PROVINCE_FEATURES), dtype=np.float32)
        owner_seat_idx = np.zeros(num_nodes, dtype=np.int64)
        province_counts: dict[int, int] = {}

        for province in provinces.values():
            if isinstance(province, LandProvince) and province.owner_id > 0:
                province_counts[province.owner_id] = province_counts.get(province.owner_id, 0) + 1

            node_idx = self.id_to_index.get(province.id)
            if node_idx is None:
                continue
            node_features[node_idx] = build_province_feature_vector(
                province, ut_map, capital_province_ids
            )
            owner_seat_idx[node_idx] = build_owner_seat_idx(province, self.seat_idx)

        player_features = np.zeros((len(self.player_ids), NUM_PLAYER_FEATURES), dtype=np.float32)
        alive_mask = np.zeros(len(self.player_ids), dtype=bool)
        for i, player_id in enumerate(self.player_ids):
            profile = players.get(player_id)
            if profile is None:
                continue
            player_features[i] = build_player_feature_vector(
                profile, province_counts.get(player_id, 0)
            )
            alive_mask[i] = not profile.defeated

        return {
            "node_features": torch.from_numpy(node_features),
            "owner_seat_idx": torch.from_numpy(owner_seat_idx),
            "player_features": torch.from_numpy(player_features),
            "alive_mask": torch.from_numpy(alive_mask),
        }

    def to_model_input(self, ritf: ReplayInterface) -> GnnBatch | None:
        """Builds a batch-of-1 `GnnBatch` from the buffered history plus a freshly
        captured "now" snapshot (always recomputed for freshness)."""
        game_state = ritf.game_state
        if game_state is None:
            return None

        now_snapshot = self._capture(game_state)
        if now_snapshot is None:
            return None

        # Right-align: older buffered snapshots + a fresh "now" in the last slot.
        history = self._snapshots[:-1] if self._snapshots else []
        steps = history[-(self.max_steps - 1) :] + [now_snapshot]
        num_valid = len(steps)

        num_nodes = self.province_graph.num_nodes
        num_players = len(self.player_ids)
        node_features = torch.zeros(T_STEPS, num_nodes, NUM_PROVINCE_FEATURES)
        owner_seat_idx = torch.zeros(T_STEPS, num_nodes, dtype=torch.long)
        player_features = torch.zeros(T_STEPS, num_players, NUM_PLAYER_FEATURES)
        alive_mask = torch.zeros(T_STEPS, num_players, dtype=torch.bool)
        time_mask = torch.zeros(T_STEPS, dtype=torch.bool)

        offset = T_STEPS - num_valid
        for i, snapshot in enumerate(steps):
            t = offset + i
            node_features[t] = snapshot["node_features"]
            owner_seat_idx[t] = snapshot["owner_seat_idx"]
            player_features[t] = snapshot["player_features"]
            alive_mask[t] = snapshot["alive_mask"]
            time_mask[t] = True

        day_of_game = (ritf.current_time - ritf.start_time).total_seconds() / 86400.0

        sample = {
            "game_id": ritf.game_id or 0,
            "node_features": node_features,
            "edge_index": self.edge_index,
            "owner_seat_idx": owner_seat_idx,
            "player_features": player_features,
            "alive_mask": alive_mask,
            "time_mask": time_mask,
            "target": torch.zeros(num_players),
            "player_ids": torch.tensor(self.player_ids, dtype=torch.long),
            "day_of_game": torch.tensor(day_of_game, dtype=torch.float32),
        }
        return collate_fn([sample])
