"""
Train the LightGBM win-probability model.

Uses GroupKFold by game_id to prevent data leakage across games.
Class imbalance (~1/64 positive rate) is handled via is_unbalance=True.
"""
from __future__ import annotations

import logging
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

from .features import feature_cols, load_dataset
from .predict import calibrator_path

logger = logging.getLogger(__name__)

_LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "is_unbalance": True,
    "num_leaves": 63,
    "learning_rate": 0.05,
    "min_child_samples": 20,
    "verbose": -1,
}
_N_ESTIMATORS = 1000
_EARLY_STOPPING_ROUNDS = 50
_LOG_EVAL_PERIOD = 100


def train(
    dataset_path: Path,
    output_path: Path,
    n_folds: int = 5,
    min_coverage: int = 1,
) -> None:
    logger.info("Loading dataset from %s", dataset_path)
    df = load_dataset(dataset_path)

    if min_coverage > 1:
        before = len(df)
        df = df[df["bucket_coverage"] >= min_coverage].reset_index(drop=True)
        logger.info("Filtered to coverage >= %d: %d → %d rows", min_coverage, before, len(df))

    cols = feature_cols(df)
    X = df[cols].values
    y = df["is_winner"].astype(int).values
    groups = df["game_id"].values

    logger.info(
        "Dataset: %d rows, %d features, %.4f positive rate",
        len(df), len(cols), y.mean(),
    )

    gkf = GroupKFold(n_splits=n_folds)
    oof_preds = np.zeros(len(df), dtype=np.float32)
    fold_aucs: list[float] = []

    for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups)):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        train_ds = lgb.Dataset(X_tr, label=y_tr, feature_name=cols)
        val_ds = lgb.Dataset(X_val, label=y_val, feature_name=cols, reference=train_ds)

        model = lgb.train(
            _LGB_PARAMS,
            train_ds,
            num_boost_round=_N_ESTIMATORS,
            valid_sets=[val_ds],
            callbacks=[
                lgb.early_stopping(_EARLY_STOPPING_ROUNDS, verbose=False),
                lgb.log_evaluation(_LOG_EVAL_PERIOD),
            ],
        )

        preds = model.predict(X_val)
        oof_preds[val_idx] = preds
        fold_auc = roc_auc_score(y_val, preds)
        fold_aucs.append(fold_auc)
        logger.info("Fold %d/%d  AUC=%.4f  trees=%d", fold + 1, n_folds, fold_auc, model.num_trees())

    oof_auc = roc_auc_score(y, oof_preds)
    logger.info("OOF AUC=%.4f  (folds: %s)", oof_auc, ", ".join(f"{a:.4f}" for a in fold_aucs))

    # `is_unbalance=True` makes raw predictions reflect a rebalanced ~50/50 prior
    # rather than the true ~3% positive rate, so they rank well (AUC) but are
    # systematically overconfident as probabilities. Fit a monotonic post-hoc
    # calibrator on the leak-free OOF predictions to map raw scores back to true
    # probabilities without touching the (good) ranking behaviour.
    calibrator = IsotonicRegression(out_of_bounds="clip").fit(oof_preds, y)
    raw_brier = brier_score_loss(y, oof_preds)
    calibrated_brier = brier_score_loss(y, calibrator.predict(oof_preds))
    logger.info(
        "OOF Brier score: raw=%.4f  calibrated=%.4f", raw_brier, calibrated_brier
    )

    # AUC breakdown by pct_game bucket — shows how predictive each time window is
    logger.info("AUC by pct_game:")
    for pct in sorted(df["pct_game"].unique()):
        mask = df["pct_game"].values == pct
        if mask.sum() < 10:
            continue
        auc = roc_auc_score(y[mask], oof_preds[mask])
        logger.info("  pct=%3d  n=%6d  AUC=%.4f", pct, mask.sum(), auc)

    # Retrain on full dataset
    logger.info("Retraining final model on all %d rows", len(df))
    full_ds = lgb.Dataset(X, label=y, feature_name=cols)
    best_trees = int(np.median([m for m in [model.num_trees()]]))  # use last fold's count
    final_model = lgb.train(
        {**_LGB_PARAMS, "verbose": -1},
        full_ds,
        num_boost_round=best_trees,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_model.save_model(str(output_path))
    logger.info("Model saved to %s", output_path)

    calib_path = calibrator_path(output_path)
    joblib.dump(calibrator, calib_path)
    logger.info("Calibrator saved to %s", calib_path)
