"""Permutation-equivariant Transformer over the (variable-size) set of players.

No positional embedding — player order carries no meaning. `src_key_padding_mask`
hides padded player slots (beyond the game's actual player count).
"""
from __future__ import annotations

import torch
from torch import nn


class PlayerSetTransformer(nn.Module):
    def __init__(
        self,
        d_model: int = 128,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

    def forward(self, x: torch.Tensor, player_mask: torch.Tensor) -> torch.Tensor:
        """
        x: [B, P_max, D]
        player_mask: [B, P_max] bool — True for real (non-padding) player slots
        """
        return self.encoder(x, src_key_padding_mask=~player_mask)
