"""Load a trained `WinPredictor` checkpoint and run inference."""
from __future__ import annotations

import logging
from pathlib import Path

import torch
import torch.nn.functional as F

from .data.dataset import GnnBatch
from .model.win_predictor import WinPredictor
from .train import building_vocab_hash, unit_vocab_hash

logger = logging.getLogger(__name__)


def load_model(checkpoint_path: Path, device: str = "cpu") -> WinPredictor:
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)

    expected_hash = checkpoint.get("building_vocab_hash")
    if expected_hash is not None and expected_hash != building_vocab_hash():
        raise ValueError(
            f"Checkpoint {checkpoint_path} was trained against a different building_vocab.json "
            f"(hash {expected_hash} != {building_vocab_hash()}). Re-extract the dataset and retrain."
        )

    expected_unit_hash = checkpoint.get("unit_vocab_hash")
    if expected_unit_hash is not None and expected_unit_hash != unit_vocab_hash():
        raise ValueError(
            f"Checkpoint {checkpoint_path} was trained against a different unit_vocab.json "
            f"(hash {expected_unit_hash} != {unit_vocab_hash()}). Re-extract the dataset and retrain."
        )

    model = WinPredictor(**checkpoint["config"])
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    return model


class Predictor:
    """Wraps a trained `WinPredictor` for batch-of-one inference."""

    def __init__(self, checkpoint_path: Path, device: str = "cpu") -> None:
        self.device = device
        self.model = load_model(checkpoint_path, device)

    @torch.no_grad()
    def predict(self, batch: GnnBatch) -> dict[int, float]:
        """`batch` must have `batch_size == 1`. Returns `{player_id: win_share}`."""
        if batch.batch_size != 1:
            raise ValueError(f"Predictor.predict expects batch_size=1, got {batch.batch_size}")

        logits = self.model(batch)
        probs = F.softmax(logits, dim=-1)[0]
        mask = batch.player_mask[0]
        player_ids = batch.player_ids[0]
        return {int(player_ids[i].item()): float(probs[i].item()) for i in range(mask.shape[0]) if mask[i]}
