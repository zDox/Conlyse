"""
Real-time win-probability inference.

Usage:
    predictor = Predictor(Path("model.lgb"))
    probs = predictor.predict(snapshots)   # {player_id: win_probability}

`snapshots` is a list of dicts with the same keys as TrainingRow.to_dict():
    province_count, vp, money_production, supply_production, fuel_production,
    component_production, electronic_production, rare_material_production,
    national_morale, is_ai, total_players, pct_game, bucket_coverage,
    and optionally bld_<group> / bld_<group>_t<tier> building-count columns.

The caller is responsible for building these from the live game state.
Probabilities are calibrated to reflect true win likelihoods (via a sidecar
isotonic-regression calibrator bundled alongside the model — see `train.py`)
when one is available, otherwise they fall back to raw model outputs. They are
not normalised to sum to 1.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import lightgbm as lgb
import pandas as pd

from .features import engineer_features

if TYPE_CHECKING:
    from sklearn.isotonic import IsotonicRegression

logger = logging.getLogger(__name__)


def calibrator_path(model_path: Path) -> Path:
    """Sidecar path for the post-hoc probability calibrator next to a model file."""
    return model_path.with_suffix(".calibrator.joblib")


def load_calibrator(model_path: Path) -> "IsotonicRegression | None":
    """Load the sidecar calibrator for `model_path`, or `None` if not bundled."""
    path = calibrator_path(model_path)
    if not path.exists():
        return None
    try:
        import joblib

        return joblib.load(path)
    except Exception:
        logger.exception("Failed to load win-probability calibrator from %s", path)
        return None


class Predictor:
    def __init__(self, model_path: Path) -> None:
        self._model = lgb.Booster(model_file=str(model_path))
        self._calibrator = load_calibrator(model_path)

    def predict(self, snapshots: list[dict]) -> dict[int, float]:
        """
        Return {player_id: win_probability} for each entry in snapshots.

        snapshots must all share the same (game_id, pct_game) so that relative
        rank features are computed correctly.  Callers should pass all alive
        players in a single call for one tick.
        """
        if not snapshots:
            return {}

        df = pd.DataFrame(snapshots)

        # Assign synthetic game_id if not provided (needed by engineer_features groupby)
        if "game_id" not in df.columns:
            df["game_id"] = 0
        if "player_id" not in df.columns:
            df["player_id"] = range(len(df))
        if "bucket_coverage" not in df.columns:
            df["bucket_coverage"] = 1

        df = engineer_features(df)

        # Use the exact feature-column list the model was trained with
        # (persisted in the model file via lgb.Dataset(feature_name=...)).
        cols = self._model.feature_name()
        for col in cols:
            if col not in df.columns:
                df[col] = 0.0

        X = df[cols].values
        probs = self._model.predict(X)
        if self._calibrator is not None:
            probs = self._calibrator.predict(probs)

        return {s["player_id"]: float(probs[i]) for i, s in enumerate(snapshots)}
