"""Per-player feature vector — a residual input to player pooling."""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
from conflict_interface.data_types.newest.player_state.faction import Faction
from conflict_interface.data_types.newest.player_state.player_profile import PlayerProfile

from .newspaper_features import NUM_NEWSPAPER_FEATURES

_FACTIONS = list(Faction)

# is_ai, is_native_ai, is_alive, team_id, province_count, total_vp, national_morale
_NUM_SCALAR_FEATURES = 7

# Changing NUM_PLAYER_FEATURES invalidates existing checkpoints — always retrain from scratch.
NUM_PLAYER_FEATURES = _NUM_SCALAR_FEATURES + len(_FACTIONS) + NUM_NEWSPAPER_FEATURES


def _one_hot(members: list, value) -> np.ndarray:
    vec = np.zeros(len(members), dtype=np.float32)
    if value is None:
        return vec
    value_val = getattr(value, "value", value)
    for i, member in enumerate(members):
        if member.value == value_val:
            vec[i] = 1.0
            break
    return vec


def build_player_feature_vector(
    profile: PlayerProfile,
    province_count: int,
    newspaper_features: Optional[np.ndarray] = None,
) -> np.ndarray:
    scalars = np.array(
        [
            1.0 if profile.computer_player else 0.0,
            1.0 if profile.native_computer else 0.0,
            0.0 if profile.defeated else 1.0,
            float(profile.team_id),
            math.log1p(max(0, province_count)),
            math.log1p(max(0, profile.victory_points or 0)),
            float(profile.average_national_morale or 0.0) / 100.0,
        ],
        dtype=np.float32,
    )
    faction_vec = _one_hot(_FACTIONS, profile.faction)
    news_vec = newspaper_features if newspaper_features is not None else np.zeros(NUM_NEWSPAPER_FEATURES, dtype=np.float32)
    return np.concatenate([scalars, faction_vec, news_vec])
