"""
Feature engineering for win-probability model.

Adds relative-rank and momentum features on top of the raw TrainingRow columns.
`FEATURE_COLS` is the single source of truth used by both train.py and predict.py.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Raw columns from TrainingRow.to_dict() that the model uses as input.
# Momentum and rank columns are added by engineer_features().
_RAW_COLS = [
    "pct_game",
    "bucket_coverage",
    "province_count",
    "vp",
    "money_production",
    "supply_production",
    "fuel_production",
    "component_production",
    "electronic_production",
    "rare_material_production",
    "national_morale",
    "is_ai",
    "total_players",
]

# Engineered columns appended by engineer_features()
_ENGINEERED_COLS = [
    "province_rank",
    "province_share",
    "vp_rank",
    "vp_share",
    "money_rank",
    "province_momentum",
    "vp_momentum",
    "is_alive",
]

FEATURE_COLS: list[str] = _RAW_COLS + _ENGINEERED_COLS


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add relative-rank and momentum features in-place (returns the same df).

    Relative features group by (game_id, pct_game) — comparing all players
    in the same snapshot.

    Momentum features group by (game_id, player_id) — comparing a player's
    current state to the previous observed bucket.  When no prior row exists
    (first snapshot or gap), momentum is NaN; LightGBM handles NaN natively.
    """
    df = df.copy()

    # ── Relative rank features ────────────────────────────────────────────
    snap = df.groupby(["game_id", "pct_game"], sort=False)

    df["province_rank"] = snap["province_count"].rank(method="dense", ascending=True)
    total_prov = snap["province_count"].transform("sum").clip(lower=1)
    df["province_share"] = df["province_count"] / total_prov

    df["vp_rank"] = snap["vp"].rank(method="dense", ascending=True)
    total_vp = snap["vp"].transform("sum").clip(lower=1)
    df["vp_share"] = df["vp"] / total_vp

    df["money_rank"] = snap["money_production"].rank(method="dense", ascending=True)

    # ── Momentum features ─────────────────────────────────────────────────
    # Sort so diff() looks back to the previous observed bucket for each player.
    df = df.sort_values(["game_id", "player_id", "pct_game"])
    player_grp = df.groupby(["game_id", "player_id"], sort=False)

    df["province_momentum"] = player_grp["province_count"].diff()
    df["vp_momentum"] = player_grp["vp"].diff()

    # ── Derived ───────────────────────────────────────────────────────────
    df["is_alive"] = (df["province_count"] > 0).astype(int)

    # Ensure all feature columns are present (building columns are variable)
    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0.0

    return df


def load_dataset(path: Path) -> pd.DataFrame:
    """Load training Parquet and apply feature engineering."""
    df = pd.read_parquet(path)
    return engineer_features(df)
