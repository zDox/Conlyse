"""GNN over the province graph — shared across all `B*T` snapshots via a PyG `Batch`."""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn
from torch_geometric.nn import GATv2Conv

from . import MAX_SEATS


class ProvinceGNN(nn.Module):
    def __init__(
        self,
        num_node_features: int,
        hidden_dim: int = 128,
        seat_embed_dim: int = 16,
        num_layers: int = 3,
        heads: int = 4,
        dropout: float = 0.1,
        max_seats: int = MAX_SEATS,
    ):
        super().__init__()
        self.seat_embedding = nn.Embedding(max_seats + 1, seat_embed_dim)
        self.input_proj = nn.Linear(num_node_features + seat_embed_dim, hidden_dim)
        self.convs = nn.ModuleList(
            [GATv2Conv(hidden_dim, hidden_dim // heads, heads=heads, dropout=dropout) for _ in range(num_layers)]
        )
        self.norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers)])
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, owner_seat_idx: torch.Tensor) -> torch.Tensor:
        seat_emb = self.seat_embedding(owner_seat_idx)
        h = F.relu(self.input_proj(torch.cat([x, seat_emb], dim=-1)))
        for conv, norm in zip(self.convs, self.norms):
            residual = h
            h = F.relu(conv(h, edge_index))
            h = self.dropout(h)
            h = norm(h + residual)
        return h
