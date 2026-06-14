"""Transformer over the `T_STEPS` resampled snapshots, per player.

Output is read from the last (rightmost / "now") position. `src_key_padding_mask`
handles cold-start games where only the last step is valid (`time_mask.sum() == 1`) —
attention degenerates to that single position.
"""
from __future__ import annotations

import torch
from torch import nn

from ml.data.resampling import T_STEPS


class TemporalTransformer(nn.Module):
    def __init__(
        self,
        d_model: int = 128,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
        max_len: int = T_STEPS,
    ):
        super().__init__()
        self.pos_embedding = nn.Embedding(max_len, d_model)
        self.day_proj = nn.Linear(1, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

    def forward(self, x: torch.Tensor, time_mask: torch.Tensor, day_of_game: torch.Tensor) -> torch.Tensor:
        """
        x: [B, T, D]
        time_mask: [B, T] bool — True for valid (non-padded) steps
        day_of_game: [B, 1] — "now" in days since game start (broadcast over T)
        """
        seq_len = x.shape[1]
        positions = torch.arange(seq_len, device=x.device)
        x = x + self.pos_embedding(positions).unsqueeze(0) + self.day_proj(day_of_game / 60.0).unsqueeze(1)
        out = self.encoder(x, src_key_padding_mask=~time_mask)
        return out[:, -1, :]
