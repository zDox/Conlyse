"""
Generate an HTML evaluation report for the GNN win predictor.

Combines the overall metrics from `ml.train.evaluate` (KL-divergence, masked Brier
score, top-k accuracy, coalition mass recovered) with a reliability diagram over
per-player win-share predictions and a breakdown of those metrics by game progress
(`day_of_game`).
"""
from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.calibration import calibration_curve
from torch.utils.data import DataLoader

from .data.dataset import GnnWinDataset, collate_fn
from .predict import load_model
from .train import evaluate, to_device

logger = logging.getLogger(__name__)

_CSS = """
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; max-width: 980px;
       margin: 2rem auto; padding: 0 1rem; color: #1f2937; line-height: 1.5; }
h1 { font-size: 1.6rem; }
h2 { margin-top: 2.5rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3rem; }
h3 { margin-top: 1.5rem; }
table { border-collapse: collapse; margin: 0.75rem 0; font-size: 0.9rem; }
th, td { border: 1px solid #e5e7eb; padding: 0.35rem 0.6rem; text-align: right; }
th { background: #f3f4f6; }
td:first-child, th:first-child { text-align: left; }
img { max-width: 100%; display: block; margin: 1rem 0; }
code { background: #f3f4f6; padding: 0.1rem 0.35rem; border-radius: 4px; }
.metrics { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
.metric { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
          padding: 0.75rem 1.25rem; min-width: 140px; }
.metric .label { font-size: 0.78rem; color: #6b7280; text-transform: uppercase; }
.metric .value { font-size: 1.4rem; font-weight: 600; }
.note { color: #6b7280; font-size: 0.88rem; }
"""

_TOPK_VALUES = (1, 3, 5)


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _img(fig: plt.Figure, alt: str) -> str:
    return f'<img alt="{alt}" src="data:image/png;base64,{_fig_to_base64(fig)}">'


def _df_to_html_table(df: pd.DataFrame, float_fmt: str = "{:.4f}") -> str:
    def fmt(v: object) -> str:
        if isinstance(v, (float, np.floating)):
            return float_fmt.format(v)
        if isinstance(v, (int, np.integer)):
            return f"{v:,}"
        return str(v)

    header = "".join(f"<th>{c}</th>" for c in df.columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{fmt(v)}</td>" for v in row) + "</tr>" for row in df.itertuples(index=False)
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def _metric_card(label: str, value: float, fmt: str = "{:.4f}") -> str:
    return f'<div class="metric"><div class="label">{label}</div><div class="value">{fmt.format(value)}</div></div>'


@torch.no_grad()
def _collect(model, loader: DataLoader, device: str) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Returns (flat predicted win-shares, flat is_winner labels, per-game metrics)."""
    model.eval()
    flat_probs: list[np.ndarray] = []
    flat_is_winner: list[np.ndarray] = []
    per_game_rows: list[dict] = []

    for batch in loader:
        batch = to_device(batch, device)
        logits = model(batch)
        probs = F.softmax(logits, dim=-1)
        log_probs = F.log_softmax(logits, dim=-1)
        alive_now = batch.alive_mask[:, -1, :] & batch.player_mask
        is_winner = batch.target > 0

        for i in range(batch.batch_size):
            mask = batch.player_mask[i]
            flat_probs.append(probs[i][mask].cpu().numpy())
            flat_is_winner.append(is_winner[i][mask].cpu().numpy())

            alive_i = alive_now[i]
            if alive_i.any():
                brier = float(((probs[i] - batch.target[i])[alive_i] ** 2).mean().item())
            else:
                brier = float("nan")
            kl = float(F.kl_div(log_probs[i : i + 1], batch.target[i : i + 1], reduction="batchmean").item())
            coalition_mass = float((probs[i] * is_winner[i].float()).sum().item())

            row = {
                "day_of_game": float(batch.day_of_game[i].item()),
                "brier": brier,
                "kl": kl,
                "coalition_mass": coalition_mass,
            }
            for k in _TOPK_VALUES:
                top_idx = torch.topk(probs[i], k=min(k, probs.shape[1])).indices
                row[f"top{k}"] = bool(is_winner[i][top_idx].any().item())
            per_game_rows.append(row)

    return np.concatenate(flat_probs), np.concatenate(flat_is_winner).astype(int), pd.DataFrame(per_game_rows)


def _plot_reliability(is_winner: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> tuple[plt.Figure, pd.DataFrame]:
    prob_true, prob_pred = calibration_curve(is_winner, probs, n_bins=n_bins, strategy="quantile")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    ax1.plot([0, 1], [0, 1], linestyle="--", color="#9ca3af", label="Perfectly calibrated")
    ax1.plot(prob_pred, prob_true, marker="o", color="#dc2626", label="Model")
    ax1.set_ylabel("Observed win-coalition rate")
    ax1.set_title("Reliability diagram (per-player win-share predictions)")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.hist(probs, bins=30, color="#dc2626", alpha=0.6)
    ax2.set_xlabel("Predicted win share")
    ax2.set_ylabel("Count")
    ax2.set_yscale("log")
    fig.tight_layout()

    table = pd.DataFrame({"predicted_mean": prob_pred, "observed_rate": prob_true})
    return fig, table


def _progress_breakdown(per_game: pd.DataFrame, n_bins: int = 5) -> pd.DataFrame:
    n_unique = per_game["day_of_game"].nunique()
    if n_unique > 1:
        per_game = per_game.copy()
        per_game["bucket"] = pd.qcut(per_game["day_of_game"], q=min(n_bins, n_unique), duplicates="drop")
    else:
        per_game = per_game.copy()
        per_game["bucket"] = per_game["day_of_game"].round(1).astype(str)

    rows = []
    for bucket, group in per_game.groupby("bucket"):
        rows.append(
            {
                "day_of_game": str(bucket),
                "n_games": len(group),
                "kl": float(group["kl"].mean()),
                "brier": float(group["brier"].mean()),
                "coalition_mass": float(group["coalition_mass"].mean()),
                **{f"top{k}_acc": float(group[f"top{k}"].mean()) for k in _TOPK_VALUES},
            }
        )
    return pd.DataFrame(rows)


def _plot_progress(table: pd.DataFrame) -> plt.Figure:
    x = range(len(table))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7.5), sharex=True)

    ax1.plot(x, table["kl"], marker="o", color="#dc2626", label="KL-divergence")
    ax1.plot(x, table["brier"], marker="o", color="#2563eb", label="Masked Brier")
    ax1.set_ylabel("Loss / error (lower is better)")
    ax1.set_title("Loss metrics by game progress")
    ax1.legend()
    ax1.grid(alpha=0.3)

    colors = {1: "#2563eb", 3: "#16a34a", 5: "#f59e0b"}
    for k in _TOPK_VALUES:
        ax2.plot(x, table[f"top{k}_acc"], marker="o", color=colors[k], label=f"Top-{k} accuracy")
    ax2.plot(x, table["coalition_mass"], marker="s", color="#9333ea", linestyle="--", label="Coalition mass")
    ax2.set_ylabel("Accuracy / mass")
    ax2.set_ylim(0.0, 1.05)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(table["day_of_game"], rotation=30, ha="right")
    ax2.set_xlabel("Game progress (day_of_game bucket)")
    ax2.legend()
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    return fig


def _render_html(
    *,
    dataset_dir: Path,
    checkpoint_path: Path,
    n_games: int,
    overall: dict[str, float],
    reliability_chart: str,
    reliability_table: pd.DataFrame,
    progress_chart: str,
    progress_table: pd.DataFrame,
) -> str:
    overview_metrics = "".join(
        [
            _metric_card("KL-divergence", overall["kl"]),
            _metric_card("Masked Brier score", overall["brier"]),
            _metric_card("Coalition mass recovered", overall["coalition_mass"]),
            *[_metric_card(f"Top-{k} accuracy", overall[f"top{k}_acc"]) for k in _TOPK_VALUES],
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Win-predictor model — evaluation report</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Win-predictor model — evaluation report</h1>
<p class="note">
  Dataset: <code>{dataset_dir}</code> &mdash; {n_games:,} games<br>
  Model: <code>{checkpoint_path}</code>
</p>

<h2>Overview</h2>
<div class="metrics">{overview_metrics}</div>
<p class="note">
  KL-divergence is the training loss between the predicted and target win-share
  distributions. Masked Brier score is <code>mean((pred - target)^2)</code> over
  players still alive at "now" (lower is better, 0 is perfect). Coalition mass
  recovered is the total predicted probability mass placed on the eventual winning
  coalition (1.0 is perfect). Top-k accuracy answers &ldquo;is at least one member of
  the winning coalition among the model's k highest-predicted players?&rdquo;
</p>

<h2>Reliability</h2>
<p class="note">
  Treats each player's predicted win share as a probability of being part of the
  winning coalition, and bins predictions into equal-sized quantile groups. The
  reliability curve compares the mean predicted share in each bin to the observed
  coalition-membership rate; the histogram below shows how predictions are
  distributed (log-scaled count axis).
</p>
{reliability_chart}
{_df_to_html_table(reliability_table)}

<h2>Metrics by game progress</h2>
<p class="note">
  Games are bucketed by <code>day_of_game</code> ("now" for each sample) into
  roughly equal-sized quantile groups, so this shows whether the model performs
  better on longer-running games than on early-game snapshots.
</p>
{progress_chart}
{_df_to_html_table(progress_table)}

</body>
</html>
"""


def generate_report(
    dataset_dir: Path,
    checkpoint_path: Path,
    output_path: Path,
    batch_size: int = 4,
    device: str = "cpu",
) -> None:
    logger.info("Loading dataset from %s", dataset_dir)
    dataset = GnnWinDataset(dataset_dir)
    if len(dataset) == 0:
        raise ValueError(f"No samples found in {dataset_dir}")
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)

    model = load_model(checkpoint_path, device)

    overall = evaluate(model, loader, device)
    logger.info("Overall metrics: %s", overall)

    probs, is_winner, per_game = _collect(model, loader, device)

    reliability_fig, reliability_table = _plot_reliability(is_winner, probs)
    reliability_chart = _img(reliability_fig, "Reliability diagram")

    progress_table = _progress_breakdown(per_game)
    progress_chart = _img(_plot_progress(progress_table), "Metrics by game progress")

    html = _render_html(
        dataset_dir=dataset_dir,
        checkpoint_path=checkpoint_path,
        n_games=len(dataset),
        overall=overall,
        reliability_chart=reliability_chart,
        reliability_table=reliability_table,
        progress_chart=progress_chart,
        progress_table=progress_table,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info("Report written to %s", output_path)
