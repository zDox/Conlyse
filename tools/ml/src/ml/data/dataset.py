"""PyTorch Dataset + collate for GNN win-predictor samples produced by `gnn-extract`.

Each `game_*.pt` file holds a shared per-game snapshot pool (delta-encoded across
days) plus `NUM_ANCHORS` anchors that each reference a `[T_STEPS]` slice of that pool
— see `gnn_extractor.extractor`. `GnnWinDataset` exposes one sample per anchor,
reconstructing the dense pool on first access to a file (cached per dataset instance)
and slicing out the requested anchor's `[T_STEPS, ...]` view.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import Dataset
from torch_geometric.data import Batch, Data

from ml.data.resampling import NUM_ANCHORS, T_STEPS

_POOL_CACHE_SIZE = 2


def _reconstruct_pool(sample: dict) -> tuple[torch.Tensor, torch.Tensor]:
    """Reconstruct the dense per-day `(node_features, owner_seat_idx)` pool from its
    delta encoding (day 0 in full, later days store only changed provinces)."""
    num_snapshots = sample["snapshot_days"].shape[0]
    num_nodes, num_features = sample["node_features_first"].shape

    node_features = torch.empty(num_snapshots, num_nodes, num_features)
    owner_seat_idx = torch.empty(num_snapshots, num_nodes, dtype=torch.int64)
    node_features[0] = sample["node_features_first"]
    owner_seat_idx[0] = sample["owner_seat_idx_first"]

    for k in range(1, num_snapshots):
        node_features[k] = node_features[k - 1]
        owner_seat_idx[k] = owner_seat_idx[k - 1]
        idx = sample["node_features_delta_idx"][k - 1]
        if idx.numel() > 0:
            node_features[k, idx] = sample["node_features_delta_val"][k - 1]
            owner_seat_idx[k, idx] = sample["owner_seat_idx_delta_val"][k - 1]

    return node_features, owner_seat_idx


def _build_anchor_sample(
    sample: dict, anchor_idx: int, pool: tuple[torch.Tensor, torch.Tensor]
) -> dict:
    """Slice out anchor `anchor_idx`'s dense `[T_STEPS, ...]` view from the shared
    per-game snapshot pool, in the format expected by `collate_fn`."""
    node_features_pool, owner_seat_idx_pool = pool
    num_nodes, num_features = sample["node_features_first"].shape
    num_players = sample["player_features"].shape[1]

    step_to_pool_idx = sample["step_to_pool_idx"][anchor_idx]
    time_mask = sample["time_mask"][anchor_idx]

    node_features = torch.zeros(T_STEPS, num_nodes, num_features)
    owner_seat_idx = torch.zeros(T_STEPS, num_nodes, dtype=torch.int64)
    player_features = torch.zeros(T_STEPS, num_players, sample["player_features"].shape[2])
    alive_mask = torch.zeros(T_STEPS, num_players, dtype=torch.bool)

    valid_steps = time_mask.nonzero(as_tuple=True)[0]
    pool_idx = step_to_pool_idx[valid_steps]
    node_features[valid_steps] = node_features_pool[pool_idx]
    owner_seat_idx[valid_steps] = owner_seat_idx_pool[pool_idx]
    player_features[valid_steps] = sample["player_features"][pool_idx]
    alive_mask[valid_steps] = sample["alive_mask"][pool_idx]

    return {
        "game_id": sample["game_id"],
        "node_ids": sample["node_ids"],
        "edge_index": sample["edge_index"],
        "node_features": node_features,
        "owner_seat_idx": owner_seat_idx,
        "player_features": player_features,
        "alive_mask": alive_mask,
        "time_mask": time_mask,
        "target": sample["target"],
        "player_ids": sample["player_ids"],
        "day_of_game": sample["anchor_day_of_game"][anchor_idx],
        "game_progress": torch.tensor((anchor_idx + 0.5) / NUM_ANCHORS, dtype=torch.float32),
    }


class GnnWinDataset(Dataset):
    def __init__(self, data_dir: Path, game_ids: list[int] | None = None):
        self.data_dir = Path(data_dir)
        if game_ids is not None:
            self.files = [self.data_dir / f"game_{game_id}.pt" for game_id in game_ids]
        else:
            self.files = sorted(self.data_dir.glob("game_*.pt"))
        self.file_game_ids = [int(f.stem.removeprefix("game_")) for f in self.files]
        self._pool_cache: OrderedDict[Path, tuple[dict, tuple[torch.Tensor, torch.Tensor]]] = (
            OrderedDict()
        )

    def __len__(self) -> int:
        return len(self.files) * NUM_ANCHORS

    def __getitem__(self, idx: int) -> dict:
        file_idx, anchor_idx = divmod(idx, NUM_ANCHORS)
        file_path = self.files[file_idx]

        cached = self._pool_cache.get(file_path)
        if cached is None:
            sample = torch.load(file_path, weights_only=False)
            cached = (sample, _reconstruct_pool(sample))
            self._pool_cache[file_path] = cached
            if len(self._pool_cache) > _POOL_CACHE_SIZE:
                self._pool_cache.popitem(last=False)
        else:
            self._pool_cache.move_to_end(file_path)

        sample, pool = cached
        return _build_anchor_sample(sample, anchor_idx, pool)


@dataclass
class GnnBatch:
    graph_batch: Batch  # B*T province graphs, flattened
    player_features: torch.Tensor  # [B, T, P_max, F_player]
    alive_mask: torch.Tensor  # [B, T, P_max] bool
    player_mask: torch.Tensor  # [B, P_max] bool — True for real (non-padding) player slots
    time_mask: torch.Tensor  # [B, T] bool
    target: torch.Tensor  # [B, P_max]
    player_ids: torch.Tensor  # [B, P_max] long — 0 for padding
    game_ids: torch.Tensor  # [B] long
    day_of_game: torch.Tensor  # [B] float — "now" in days since game start
    game_progress: (
        torch.Tensor
    )  # [B] float — fraction of the game elapsed at "now" (NaN if unknown)
    batch_size: int
    num_steps: int
    max_players: int


def collate_fn(samples: list[dict]) -> GnnBatch:
    batch_size = len(samples)
    num_steps = samples[0]["node_features"].shape[0]
    max_players = max(sample["player_features"].shape[1] for sample in samples)

    graphs = [
        Data(
            x=sample["node_features"][t],
            edge_index=sample["edge_index"],
            owner_seat_idx=sample["owner_seat_idx"][t],
        )
        for sample in samples
        for t in range(num_steps)
    ]
    graph_batch = Batch.from_data_list(graphs)

    player_features = torch.zeros(
        batch_size, num_steps, max_players, samples[0]["player_features"].shape[2]
    )
    alive_mask = torch.zeros(batch_size, num_steps, max_players, dtype=torch.bool)
    player_mask = torch.zeros(batch_size, max_players, dtype=torch.bool)
    target = torch.zeros(batch_size, max_players)
    player_ids = torch.zeros(batch_size, max_players, dtype=torch.long)
    time_mask = torch.stack([sample["time_mask"] for sample in samples])
    game_ids = torch.tensor([sample["game_id"] for sample in samples], dtype=torch.long)
    day_of_game = torch.stack([sample["day_of_game"] for sample in samples])
    game_progress = torch.stack(
        [sample.get("game_progress", torch.tensor(float("nan"))) for sample in samples]
    )

    for i, sample in enumerate(samples):
        num_players = sample["player_features"].shape[1]
        player_features[i, :, :num_players] = sample["player_features"]
        alive_mask[i, :, :num_players] = sample["alive_mask"]
        player_mask[i, :num_players] = True
        target[i, :num_players] = sample["target"]
        player_ids[i, :num_players] = sample["player_ids"]

    return GnnBatch(
        graph_batch=graph_batch,
        player_features=player_features,
        alive_mask=alive_mask,
        player_mask=player_mask,
        time_mask=time_mask,
        target=target,
        player_ids=player_ids,
        game_ids=game_ids,
        day_of_game=day_of_game,
        game_progress=game_progress,
        batch_size=batch_size,
        num_steps=num_steps,
        max_players=max_players,
    )
