"""
Win-coalition target vector.

`determine_winner_ids` is a duplicated equivalent of `_determine_winners` in
`tools/game_stats_extractor/src/game_stats_extractor/extractors/replay_extractor.py`
(the source of truth), operating directly on `PlayerProfile` instead of the
extractor's `PlayerData` to avoid a cross-package dependency.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from conflict_interface.data_types.newest.newspaper_state.ranking import Ranking
from conflict_interface.data_types.newest.player_state.player_profile import PlayerProfile


def determine_winner_ids(
    profiles: list[PlayerProfile],
    ranking: Optional[Ranking] = None,
) -> list[int]:
    if not profiles:
        return []

    if ranking is not None and ranking.initialized:
        if ranking.winner != -1:
            return [ranking.winner]
        if ranking.winner_team != -1:
            return [p.player_id for p in profiles if p.team_id == ranking.winner_team]

    still_playing = [p for p in profiles if p.playing and not p.defeated]

    if len(still_playing) == 1:
        return [still_playing[0].player_id]

    if len(still_playing) >= 2:
        team_ids = {p.team_id for p in still_playing if p.team_id > 0}
        if len(team_ids) == 1 and all(p.team_id > 0 for p in still_playing):
            return [p.player_id for p in still_playing]

    pool = still_playing or [p for p in profiles if not p.defeated] or profiles
    max_vp = max((p.victory_points for p in pool), default=0)
    if max_vp <= 0:
        return []

    threshold = max_vp * 0.9
    winners = [p for p in pool if p.victory_points >= threshold]

    if len(winners) == 1:
        return [winners[0].player_id]

    team_ids = {p.team_id for p in winners if p.team_id > 0}
    if len(team_ids) == 1:
        return [p.player_id for p in winners]

    top = max(winners, key=lambda p: p.victory_points)
    return [top.player_id]


def compute_target_vector(winner_ids: list[int], player_ids: list[int]) -> np.ndarray:
    """`1/k` for players in the winning coalition (k = coalition size), else 0. Sums to 1."""
    winner_set = set(winner_ids)
    k = len(winner_set)
    if k == 0:
        return np.zeros(len(player_ids), dtype=np.float32)
    return np.array([1.0 / k if pid in winner_set else 0.0 for pid in player_ids], dtype=np.float32)
