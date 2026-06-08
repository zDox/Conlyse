"""
Generate a detailed HTML evaluation report for the win-probability model.

Combines discrimination (AUC, PR-AUC, top-k accuracy), calibration (Brier score,
reliability diagram) and feature-importance diagnostics into a single
self-contained HTML file with charts embedded as base64 PNGs.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_recall_curve,
    roc_auc_score,
)

from .features import load_dataset

logger = logging.getLogger(__name__)

_TOPK_VALUES = (1, 2, 3)
_MIN_BUCKET_N = 10  # mirrors the bucket-size filter used by `conlyse-predict eval`

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
        "<tr>" + "".join(f"<td>{fmt(v)}</td>" for v in row) + "</tr>"
        for row in df.itertuples(index=False)
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def _load_predictions(
    dataset_path: Path, model_path: Path, min_coverage: int
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, lgb.Booster]:
    df = load_dataset(dataset_path)

    if min_coverage > 1:
        before = len(df)
        df = df[df["bucket_coverage"] >= min_coverage].reset_index(drop=True)
        logger.info("Filtered to coverage >= %d: %d -> %d rows", min_coverage, before, len(df))

    model = lgb.Booster(model_file=str(model_path))
    cols = model.feature_name()

    for col in cols:
        if col not in df.columns:
            df[col] = 0.0

    X = df[cols].values
    y = df["is_winner"].astype(int).values
    preds = model.predict(X)
    df = df.copy()
    df["pred"] = preds
    return df, y, preds, model


# ── Discrimination over game progress ───────────────────────────────────────


def _auc_by_pct(df: pd.DataFrame, y: np.ndarray, preds: np.ndarray) -> pd.DataFrame:
    rows = []
    for pct in sorted(df["pct_game"].unique()):
        mask = df["pct_game"].values == pct
        if mask.sum() < _MIN_BUCKET_N:
            continue
        rows.append(
            {
                "pct_game": int(pct),
                "n": int(mask.sum()),
                "auc": float(roc_auc_score(y[mask], preds[mask])),
                "pos_rate": float(y[mask].mean()),
            }
        )
    return pd.DataFrame(rows)


def _plot_auc_by_pct(table: pd.DataFrame) -> plt.Figure:
    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.plot(table["pct_game"], table["auc"], marker="o", color="#2563eb", label="AUC")
    ax1.set_xlabel("Game progress (%)")
    ax1.set_ylabel("AUC", color="#2563eb")
    ax1.set_ylim(0.5, 1.0)
    ax1.tick_params(axis="y", labelcolor="#2563eb")
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()
    ax2.bar(table["pct_game"], table["n"], width=3.0, alpha=0.15, color="#9333ea")
    ax2.set_ylabel("Snapshot rows (n)", color="#9333ea")
    ax2.tick_params(axis="y", labelcolor="#9333ea")

    ax1.set_title("Discrimination (AUC) over game progress")
    fig.tight_layout()
    return fig


# ── Imbalance-aware metrics ──────────────────────────────────────────────────


def _plot_pr_curve(y: np.ndarray, preds: np.ndarray) -> plt.Figure:
    precision, recall, _ = precision_recall_curve(y, preds)
    ap = average_precision_score(y, preds)
    baseline = float(y.mean())

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, color="#16a34a", label=f"Model (AP = {ap:.4f})")
    ax.axhline(baseline, color="#9ca3af", linestyle="--", label=f"Random baseline ({baseline:.4f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-recall curve")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def _topk_accuracy(df: pd.DataFrame, k_values: tuple[int, ...] = _TOPK_VALUES) -> dict[int, float]:
    """
    For each (game_id, pct_game) snapshot: is *any* eventual winner among the
    model's top-k ranked players?  Some games end in shared/coalition victories
    (multiple is_winner=1 rows per snapshot), so this checks presence, not count.
    """
    df = df.copy()
    df["pred_rank"] = df.groupby(["game_id", "pct_game"], sort=False)["pred"].rank(
        ascending=False, method="first"
    )
    result = {}
    for k in k_values:
        top = df[df["pred_rank"] <= k]
        hit = top.groupby(["game_id", "pct_game"], sort=False)["is_winner"].max()
        result[k] = float(hit.mean())
    return result


def _topk_accuracy_by_pct(
    df: pd.DataFrame, k_values: tuple[int, ...] = _TOPK_VALUES
) -> pd.DataFrame:
    df = df.copy()
    df["pred_rank"] = df.groupby(["game_id", "pct_game"], sort=False)["pred"].rank(
        ascending=False, method="first"
    )

    rows = []
    for pct, g in df.groupby("pct_game", sort=True):
        n_snapshots = g["game_id"].nunique()
        if n_snapshots < _MIN_BUCKET_N:
            continue
        row: dict[str, object] = {"pct_game": int(pct), "n_snapshots": int(n_snapshots)}
        for k in k_values:
            top = g[g["pred_rank"] <= k]
            hit = top.groupby("game_id", sort=False)["is_winner"].max()
            row[f"top{k}_acc"] = float(hit.mean())
        rows.append(row)
    return pd.DataFrame(rows)


def _plot_topk_by_pct(table: pd.DataFrame, k_values: tuple[int, ...] = _TOPK_VALUES) -> plt.Figure:
    colors = {1: "#2563eb", 2: "#16a34a", 3: "#f59e0b"}
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k in k_values:
        col = f"top{k}_acc"
        if col in table.columns:
            ax.plot(
                table["pct_game"], table[col], marker="o", color=colors.get(k), label=f"Top-{k}"
            )
    ax.set_xlabel("Game progress (%)")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0.0, 1.0)
    ax.set_title(
        "Top-k accuracy over game progress\n(is the eventual winner among the model's top-k picks?)"
    )
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


# ── Calibration ──────────────────────────────────────────────────────────────


def _plot_calibration(
    y: np.ndarray, preds: np.ndarray, n_bins: int = 10
) -> tuple[plt.Figure, pd.DataFrame]:
    prob_true, prob_pred = calibration_curve(y, preds, n_bins=n_bins, strategy="quantile")

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(6, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
    )
    ax1.plot([0, 1], [0, 1], linestyle="--", color="#9ca3af", label="Perfectly calibrated")
    ax1.plot(prob_pred, prob_true, marker="o", color="#dc2626", label="Model")
    ax1.set_ylabel("Observed win rate")
    ax1.set_title("Reliability diagram (quantile-binned predictions)")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.hist(preds, bins=30, color="#dc2626", alpha=0.6)
    ax2.set_xlabel("Predicted win probability")
    ax2.set_ylabel("Count")
    ax2.set_yscale("log")
    fig.tight_layout()

    table = pd.DataFrame({"predicted_mean": prob_pred, "observed_rate": prob_true})
    return fig, table


# ── Feature importance ───────────────────────────────────────────────────────


def _feature_importance_table(model: lgb.Booster) -> pd.DataFrame:
    table = pd.DataFrame(
        {
            "feature": model.feature_name(),
            "gain": model.feature_importance(importance_type="gain"),
            "split": model.feature_importance(importance_type="split"),
        }
    )
    return table.sort_values("gain", ascending=False).reset_index(drop=True)


def _plot_feature_importance(table: pd.DataFrame, top_n: int = 20) -> plt.Figure:
    top = table.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, max(4.0, 0.35 * len(top))))
    ax.barh(top["feature"], top["gain"], color="#2563eb")
    ax.set_xlabel("Gain importance")
    ax.set_title(f"Top {len(top)} features by gain")
    fig.tight_layout()
    return fig


# ── HTML rendering ───────────────────────────────────────────────────────────


def _metric_card(label: str, value: float, fmt: str = "{:.4f}") -> str:
    return (
        f'<div class="metric"><div class="label">{label}</div>'
        f'<div class="value">{fmt.format(value)}</div></div>'
    )


def _render_html(
    *,
    dataset_path: Path,
    model_path: Path,
    n_rows: int,
    pos_rate: float,
    overall_auc: float,
    overall_ap: float,
    overall_log_loss: float,
    overall_brier: float,
    topk: dict[int, float],
    auc_table: pd.DataFrame,
    auc_chart: str,
    pr_chart: str,
    topk_table: pd.DataFrame,
    topk_chart: str,
    calib_table: pd.DataFrame,
    calib_chart: str,
    fi_table: pd.DataFrame,
    fi_chart: str,
) -> str:
    overview_metrics = "".join(
        [
            _metric_card("AUC", overall_auc),
            _metric_card("PR-AUC (avg precision)", overall_ap),
            _metric_card("Log loss", overall_log_loss),
            _metric_card("Brier score", overall_brier),
            *[_metric_card(f"Top-{k} accuracy", v) for k, v in sorted(topk.items())],
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Win-probability model — evaluation report</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Win-probability model — evaluation report</h1>
<p class="note">
  Dataset: <code>{dataset_path}</code> &mdash; {n_rows:,} rows, positive rate {pos_rate:.4f}<br>
  Model: <code>{model_path}</code>
</p>

<h2>Overview</h2>
<div class="metrics">{overview_metrics}</div>
<p class="note">
  AUC measures ranking quality &mdash; the probability that a randomly chosen eventual
  winner is scored higher than a randomly chosen eventual loser. PR-AUC and log loss are
  more sensitive than AUC to the heavy class imbalance (positive rate {pos_rate:.2%}).
  Top-k accuracy answers &ldquo;is the eventual winner among the model's k highest-scored
  players at that point in the game?&rdquo; Brier score summarises calibration
  (lower is better; 0 is perfect).
</p>

<h2>Discrimination over game progress</h2>
{auc_chart}
{_df_to_html_table(auc_table)}

<h2>Imbalance-aware metrics</h2>
<p class="note">
  ROC-AUC can look strong even when a model performs poorly on a heavily imbalanced task.
  The precision-recall curve and top-k accuracy below give a more direct read on
  &ldquo;does the model actually identify the winner&rdquo; than AUC alone.
</p>
{pr_chart}
<h3>Top-k accuracy by game progress</h3>
{topk_chart}
{_df_to_html_table(topk_table)}

<h2>Calibration</h2>
<p class="note">
  A well-calibrated model's predicted probability can be read at face value
  (e.g. a displayed &ldquo;30% win chance&rdquo; should win roughly 30% of the time).
  The reliability diagram bins predictions into equal-sized quantile groups and compares
  the mean predicted probability in each bin to the observed win rate; the histogram below
  it shows how predictions are distributed (log-scaled count axis).
</p>
{calib_chart}
{_df_to_html_table(calib_table)}

<h2>Feature importance</h2>
<p class="note">
  LightGBM gain/split importance &mdash; sanity-checks that the model relies on
  meaningful signals (province control, VP, momentum/rank features) rather than
  spurious correlations.
</p>
{fi_chart}
{_df_to_html_table(fi_table)}

</body>
</html>
"""


def generate_report(
    dataset_path: Path,
    model_path: Path,
    output_path: Path,
    min_coverage: int = 1,
) -> None:
    logger.info("Loading dataset from %s", dataset_path)
    df, y, preds, model = _load_predictions(dataset_path, model_path, min_coverage)
    logger.info("Evaluating %d rows (positive rate %.4f)", len(df), y.mean())

    overall_auc = float(roc_auc_score(y, preds))
    overall_ap = float(average_precision_score(y, preds))
    overall_log_loss = float(log_loss(y, preds))
    overall_brier = float(brier_score_loss(y, preds))
    topk = _topk_accuracy(df)

    auc_table = _auc_by_pct(df, y, preds)
    auc_chart = _img(_plot_auc_by_pct(auc_table), "AUC by game progress")

    pr_chart = _img(_plot_pr_curve(y, preds), "Precision-recall curve")
    topk_table = _topk_accuracy_by_pct(df)
    topk_chart = _img(_plot_topk_by_pct(topk_table), "Top-k accuracy by game progress")

    calib_fig, calib_table = _plot_calibration(y, preds)
    calib_chart = _img(calib_fig, "Reliability diagram")

    fi_table = _feature_importance_table(model)
    fi_chart = _img(_plot_feature_importance(fi_table), "Feature importance")

    html = _render_html(
        dataset_path=dataset_path,
        model_path=model_path,
        n_rows=len(df),
        pos_rate=float(y.mean()),
        overall_auc=overall_auc,
        overall_ap=overall_ap,
        overall_log_loss=overall_log_loss,
        overall_brier=overall_brier,
        topk=topk,
        auc_table=auc_table,
        auc_chart=auc_chart,
        pr_chart=pr_chart,
        topk_table=topk_table,
        topk_chart=topk_chart,
        calib_table=calib_table,
        calib_chart=calib_chart,
        fi_table=fi_table,
        fi_chart=fi_chart,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info("Report written to %s", output_path)
