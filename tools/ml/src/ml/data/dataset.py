"""PyTorch Dataset + collate for GNN win-predictor samples produced by `gnn-extract`."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import Dataset
from torch_geometric.data import Batch, Data


class GnnWinDataset(Dataset):
    def __init__(self, data_dir: Path, game_ids: list[int] | None = None):
        self.data_dir = Path(data_dir)
        if game_ids is not None:
            self.files = [self.data_dir / f"game_{game_id}.pt" for game_id in game_ids]
        else:
            self.files = sorted(self.data_dir.glob("game_*.pt"))

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, idx: int) -> dict:
        return torch.load(self.files[idx], weights_only=False)


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

    player_features = torch.zeros(batch_size, num_steps, max_players, samples[0]["player_features"].shape[2])
    alive_mask = torch.zeros(batch_size, num_steps, max_players, dtype=torch.bool)
    player_mask = torch.zeros(batch_size, max_players, dtype=torch.bool)
    target = torch.zeros(batch_size, max_players)
    player_ids = torch.zeros(batch_size, max_players, dtype=torch.long)
    time_mask = torch.stack([sample["time_mask"] for sample in samples])
    game_ids = torch.tensor([sample["game_id"] for sample in samples], dtype=torch.long)
    day_of_game = torch.stack([sample["day_of_game"] for sample in samples])

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
        batch_size=batch_size,
        num_steps=num_steps,
        max_players=max_players,
    )
