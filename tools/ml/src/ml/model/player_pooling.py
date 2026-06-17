"""Aggregates per-province GNN embeddings into per-player embeddings.

Uses mean+max+sum scatter pooling (grouped by `owner_seat_idx`) concatenated with the
per-player feature vector and projected through an MLP — cheaper than attention pooling
and handles arbitrary province counts per player without padding. Players with 0
provinces fall back to the player-feature projection only (zero province contribution).
Sum pooling captures empire-scale totals (resource production, buildings, etc.) that
mean+max alone cannot distinguish when player province counts differ.
"""
from __future__ import annotations

import torch
from torch import nn
from torch_geometric.utils import scatter

from . import MAX_SEATS


class PlayerPooling(nn.Module):
    def __init__(
        self,
        province_dim: int,
        player_feature_dim: int,
        hidden_dim: int = 128,
        max_seats: int = MAX_SEATS,
    ):
        super().__init__()
        self.max_seats = max_seats
        self.player_feature_proj = nn.Linear(player_feature_dim, hidden_dim)
        self.mlp = nn.Sequential(
            nn.Linear(province_dim * 3 + hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )

    def forward(
        self,
        node_embeddings: torch.Tensor,  # [total_nodes, province_dim]
        owner_seat_idx: torch.Tensor,  # [total_nodes] long, 0..max_seats
        graph_index: torch.Tensor,  # [total_nodes] long, 0..num_graphs-1
        num_graphs: int,
        player_features: torch.Tensor,  # [num_graphs, P_max, F_player]
    ) -> torch.Tensor:
        num_seats = self.max_seats + 1
        combined_idx = graph_index * num_seats + owner_seat_idx
        dim_size = num_graphs * num_seats

        mean_pool = scatter(node_embeddings, combined_idx, dim=0, dim_size=dim_size, reduce="mean")
        max_pool = scatter(node_embeddings, combined_idx, dim=0, dim_size=dim_size, reduce="max")
        sum_pool = scatter(node_embeddings, combined_idx, dim=0, dim_size=dim_size, reduce="sum")

        province_dim = node_embeddings.shape[-1]
        mean_pool = mean_pool.view(num_graphs, num_seats, province_dim)
        max_pool = max_pool.view(num_graphs, num_seats, province_dim)
        sum_pool = sum_pool.view(num_graphs, num_seats, province_dim)

        num_players = player_features.shape[1]
        # Seat 0 == neutral; players occupy seats 1..num_players.
        mean_pool = mean_pool[:, 1 : 1 + num_players]
        max_pool = max_pool[:, 1 : 1 + num_players]
        sum_pool = sum_pool[:, 1 : 1 + num_players]

        province_repr = torch.cat([mean_pool, max_pool, sum_pool], dim=-1)
        player_repr = self.player_feature_proj(player_features)
        return self.mlp(torch.cat([province_repr, player_repr], dim=-1))
