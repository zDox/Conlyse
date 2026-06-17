"""
Train the GNN + Transformer win-predictor.

Each game contributes `NUM_ANCHORS` samples (one per mid-game anchor day, see
`ml.data.resampling`), so a `GroupKFold` over game ids is used — this keeps all
anchors of one game in the same fold and avoids leaking a game's outcome between
train and validation splits.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import torch
import torch.nn.functional as F
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Subset

from .data.dataset import GnnBatch, GnnWinDataset, collate_fn
from .data.newspaper_features import UNIT_VOCAB
from .data.player_features import NUM_PLAYER_FEATURES
from .data.province_features import BUILDING_VOCAB, NUM_PROVINCE_FEATURES
from .data.resampling import NUM_ANCHORS
from .model.win_predictor import WinPredictor, win_predictor_loss

logger = logging.getLogger(__name__)

_TOPK_VALUES = (1, 3, 5)


def building_vocab_hash() -> str:
    """Fingerprint of `building_vocab.json` — checkpoints fail to load if it changes."""
    return hashlib.sha256("\n".join(BUILDING_VOCAB).encode()).hexdigest()[:16]


def unit_vocab_hash() -> str:
    """Fingerprint of `unit_vocab.json` — checkpoints fail to load if it changes."""
    return hashlib.sha256("\n".join(UNIT_VOCAB).encode()).hexdigest()[:16]


def model_config() -> dict:
    return {
        "num_node_features": NUM_PROVINCE_FEATURES,
        "num_player_features": NUM_PLAYER_FEATURES,
        "hidden_dim": 128,
    }


def to_device(batch: GnnBatch, device: str) -> GnnBatch:
    return GnnBatch(
        graph_batch=batch.graph_batch.to(device),
        player_features=batch.player_features.to(device),
        alive_mask=batch.alive_mask.to(device),
        player_mask=batch.player_mask.to(device),
        time_mask=batch.time_mask.to(device),
        target=batch.target.to(device),
        player_ids=batch.player_ids.to(device),
        game_ids=batch.game_ids.to(device),
        day_of_game=batch.day_of_game.to(device),
        game_progress=batch.game_progress.to(device),
        batch_size=batch.batch_size,
        num_steps=batch.num_steps,
        max_players=batch.max_players,
    )


@torch.no_grad()
def evaluate(model: WinPredictor, loader: DataLoader, device: str) -> dict[str, float]:
    model.eval()
    total_kl = 0.0
    total_brier_sum = 0.0
    total_brier_n = 0
    coalition_mass_sum = 0.0
    topk_hits = dict.fromkeys(_TOPK_VALUES, 0)
    n_samples = 0

    for batch in loader:
        batch = to_device(batch, device)
        logits = model(batch)
        probs = F.softmax(logits, dim=-1)

        total_kl += win_predictor_loss(logits, batch.target).item() * batch.batch_size
        n_samples += batch.batch_size

        alive_now = batch.alive_mask[:, -1, :] & batch.player_mask
        sq_err = (probs - batch.target) ** 2
        total_brier_sum += sq_err[alive_now].sum().item()
        total_brier_n += int(alive_now.sum().item())

        is_winner = batch.target > 0
        coalition_mass_sum += (probs * is_winner.float()).sum(dim=-1).sum().item()

        for k in _TOPK_VALUES:
            top_idx = torch.topk(probs, k=min(k, probs.shape[1]), dim=-1).indices
            hit = is_winner.gather(1, top_idx).any(dim=-1)
            topk_hits[k] += int(hit.sum().item())

    metrics = {
        "kl": total_kl / max(1, n_samples),
        "brier": total_brier_sum / max(1, total_brier_n),
        "coalition_mass": coalition_mass_sum / max(1, n_samples),
    }
    for k in _TOPK_VALUES:
        metrics[f"top{k}_acc"] = topk_hits[k] / max(1, n_samples)
    return metrics


def _run_epoch(
    model: WinPredictor, loader: DataLoader, optimizer: torch.optim.Optimizer, device: str
) -> float:
    model.train()
    total_loss = 0.0
    n_batches = 0
    for batch in loader:
        batch = to_device(batch, device)
        optimizer.zero_grad()
        logits = model(batch)
        loss = win_predictor_loss(logits, batch.target)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        n_batches += 1
    return total_loss / max(1, n_batches)


def train(
    dataset_dir: Path,
    output_dir: Path,
    n_folds: int = 5,
    epochs: int = 20,
    batch_size: int = 4,
    lr: float = 1e-4,
    device: str = "cpu",
) -> None:
    dataset = GnnWinDataset(dataset_dir)
    n = len(dataset)
    if n == 0:
        raise ValueError(f"No samples found in {dataset_dir}")
    n_games = len(dataset.file_game_ids)
    groups = [game_id for game_id in dataset.file_game_ids for _ in range(NUM_ANCHORS)]
    logger.info("Dataset: %d games, %d samples", n_games, n)

    if n_games >= 2:
        n_folds = max(2, min(n_folds, n_games))
        gkf = GroupKFold(n_splits=n_folds)
        splits = list(gkf.split(range(n), groups=groups))
    else:
        splits = [(list(range(n)), list(range(n)))]

    fold_metrics = []
    for fold, (train_idx, val_idx) in enumerate(splits):
        logger.info(
            "Fold %d/%d: %d train, %d val games",
            fold + 1,
            len(splits),
            len(train_idx),
            len(val_idx),
        )
        train_loader = DataLoader(
            Subset(dataset, train_idx), batch_size=batch_size, shuffle=True, collate_fn=collate_fn
        )
        val_loader = DataLoader(
            Subset(dataset, val_idx), batch_size=batch_size, shuffle=False, collate_fn=collate_fn
        )

        model = WinPredictor(**model_config()).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        metrics: dict[str, float] = {}
        for epoch in range(epochs):
            train_loss = _run_epoch(model, train_loader, optimizer, device)
            metrics = evaluate(model, val_loader, device)
            logger.info(
                "Fold %d epoch %d/%d: train_loss=%.4f val_kl=%.4f val_brier=%.4f "
                "top1=%.3f top3=%.3f top5=%.3f coalition_mass=%.3f",
                fold + 1,
                epoch + 1,
                epochs,
                train_loss,
                metrics["kl"],
                metrics["brier"],
                metrics["top1_acc"],
                metrics["top3_acc"],
                metrics["top5_acc"],
                metrics["coalition_mass"],
            )
        fold_metrics.append(metrics)

    avg_metrics = {
        key: sum(m[key] for m in fold_metrics) / len(fold_metrics) for key in fold_metrics[0]
    }
    logger.info("Average validation metrics across folds: %s", avg_metrics)

    logger.info("Retraining final model on all %d games", n)
    full_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    model = WinPredictor(**model_config()).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    for epoch in range(epochs):
        train_loss = _run_epoch(model, full_loader, optimizer, device)
        logger.info("Final model epoch %d/%d: train_loss=%.4f", epoch + 1, epochs, train_loss)

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "win_predictor.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": model_config(),
            "building_vocab_hash": building_vocab_hash(),
            "unit_vocab_hash": unit_vocab_hash(),
        },
        checkpoint_path,
    )
    logger.info("Checkpoint saved to %s", checkpoint_path)
