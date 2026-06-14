"""Wires GNN -> player pooling -> temporal Transformer -> player-set Transformer -> logits.

Output is a per-player logit; `F.log_softmax` over the (masked) player dimension gives
the predicted win-coalition distribution. Train with `win_predictor_loss` (KL-divergence
against the soft `1/k` target — see `ml.data.target.compute_target_vector`).
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from ml.data.dataset import GnnBatch
from ml.data.player_features import NUM_PLAYER_FEATURES
from ml.data.province_features import NUM_PROVINCE_FEATURES

from .player_pooling import PlayerPooling
from .player_transformer import PlayerSetTransformer
from .province_gnn import ProvinceGNN
from .temporal_transformer import TemporalTransformer


class WinPredictor(nn.Module):
    def __init__(
        self,
        num_node_features: int = NUM_PROVINCE_FEATURES,
        num_player_features: int = NUM_PLAYER_FEATURES,
        hidden_dim: int = 128,
        gnn_layers: int = 3,
        temporal_layers: int = 2,
        player_set_layers: int = 2,
        heads: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.province_gnn = ProvinceGNN(
            num_node_features, hidden_dim=hidden_dim, num_layers=gnn_layers, heads=heads, dropout=dropout
        )
        self.player_pooling = PlayerPooling(hidden_dim, num_player_features, hidden_dim=hidden_dim)
        self.temporal_transformer = TemporalTransformer(
            d_model=hidden_dim, num_layers=temporal_layers, nhead=heads, dropout=dropout
        )
        self.player_transformer = PlayerSetTransformer(
            d_model=hidden_dim, num_layers=player_set_layers, nhead=heads, dropout=dropout
        )
        self.output_head = nn.Linear(hidden_dim, 1)

    def forward(self, batch: GnnBatch) -> torch.Tensor:
        """Returns per-player logits `[B, P_max]`, masked to `-inf` at padded player slots."""
        B, T, P_max = batch.batch_size, batch.num_steps, batch.max_players
        gb = batch.graph_batch

        node_embeddings = self.province_gnn(gb.x, gb.edge_index, gb.owner_seat_idx)

        player_features_flat = batch.player_features.reshape(B * T, P_max, -1)
        pooled = self.player_pooling(node_embeddings, gb.owner_seat_idx, gb.batch, B * T, player_features_flat)

        # [B*T, P_max, D] -> [B*P_max, T, D] for the per-player temporal Transformer.
        pooled = pooled.view(B, T, P_max, self.hidden_dim).permute(0, 2, 1, 3).reshape(B * P_max, T, self.hidden_dim)
        time_mask = batch.time_mask.unsqueeze(1).expand(B, P_max, T).reshape(B * P_max, T)
        day_of_game = batch.day_of_game.view(B, 1, 1).expand(B, P_max, 1).reshape(B * P_max, 1)

        temporal_out = self.temporal_transformer(pooled, time_mask, day_of_game)
        temporal_out = temporal_out.view(B, P_max, self.hidden_dim)

        player_out = self.player_transformer(temporal_out, batch.player_mask)

        logits = self.output_head(player_out).squeeze(-1)
        return logits.masked_fill(~batch.player_mask, float("-inf"))


def win_predictor_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """KL-divergence between the predicted (masked-softmax) and target distributions."""
    log_probs = F.log_softmax(logits, dim=-1)
    return F.kl_div(log_probs, target, reduction="batchmean")
