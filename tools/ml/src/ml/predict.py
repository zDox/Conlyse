"""
Real-time win-probability inference.

Usage:
    predictor = Predictor(Path("model.lgb"))
    probs = predictor.predict(snapshots)   # {player_id: win_probability}

`snapshots` is a list of dicts with the same keys as TrainingRow.to_dict():
    province_count, vp, money_production, supply_production, fuel_production,
    component_production, electronic_production, rare_material_production,
    national_morale, is_ai, total_players, pct_game, bucket_coverage,
    and optionally bld_* columns.

The caller is responsible for building these from the live game state.
Probabilities are raw model outputs (not normalised to sum to 1).
"""
from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import pandas as pd

from .features import FEATURE_COLS, engineer_features


class Predictor:
    def __init__(self, model_path: Path) -> None:
        self._model = lgb.Booster(model_file=str(model_path))

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

        # Zero-fill any missing feature columns
        for col in FEATURE_COLS:
            if col not in df.columns:
                df[col] = 0.0

        X = df[FEATURE_COLS].values
        probs = self._model.predict(X)

        return {s["player_id"]: float(probs[i]) for i, s in enumerate(snapshots)}
