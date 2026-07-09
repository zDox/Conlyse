"""
Win-coalition target vector.

`determine_winner_ids` is a duplicated equivalent of `_determine_winners` in
`tools/game_stats_extractor/src/game_stats_extractor/extractors/replay_extractor.py`
(the source of truth), operating directly on `PlayerProfile` instead of the
extractor's `PlayerData` to avoid a cross-package dependency. Keep the two in sync.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

import numpy as np
from conflict_interface.data_types.newest.newspaper_state.ranking import Ranking
from conflict_interface.data_types.newest.player_state.player_profile import PlayerProfile

# Victory-point multipliers by coalition size, i.e. a coalition of n players needs
# victory_points_modifier * _VICTORY_POINTS_FACTORS[n] combined VP to win. This mirrors
# the game's own ultshared.modding.configuration.UltTeamConfig.victoryPointsFactors table
# (confirmed against real in-game values for n=1..5); it is a fixed design table, not a
# formula, and the game caps coalitions at maxCoalitionSize=5. Sizes beyond 5 fall through
# to the relative-VP fallback below.
_VICTORY_POINTS_FACTORS = {1: 1.0, 2: 1.6, 3: 2.3, 4: 2.9, 5: 3.2}


def determine_winner_ids(
    profiles: list[PlayerProfile],
    ranking: Optional[Ranking] = None,
    victory_points_modifier: int = 0,
) -> list[int]:
    if not profiles:
        return []

    if ranking is not None and ranking.initialized:
        if ranking.winner != -1:
            return [ranking.winner]
        if ranking.winner_team != -1:
            return [p.player_id for p in profiles if p.team_id == ranking.winner_team]

    # Elimination: only one player, or one team, still standing
    still_playing = [p for p in profiles if p.playing and not p.defeated]

    if len(still_playing) == 1:
        return [still_playing[0].player_id]

    if len(still_playing) >= 2:
        team_ids = {p.team_id for p in still_playing if p.team_id > 0}
        if len(team_ids) == 1 and all(p.team_id > 0 for p in still_playing):
            return [p.player_id for p in still_playing]

    pool = still_playing or [p for p in profiles if not p.defeated] or profiles

    # Real victory-point thresholds: a single player reaching victory_points_modifier VP
    # wins solo; otherwise a team whose combined VP clears its size-scaled threshold wins.
    if victory_points_modifier > 0:
        solo_candidates = [p for p in pool if p.victory_points >= victory_points_modifier]
        if solo_candidates:
            top = max(solo_candidates, key=lambda p: p.victory_points)
            return [top.player_id]

        teams: dict[int, list[PlayerProfile]] = defaultdict(list)
        for p in pool:
            if p.team_id > 0:
                teams[p.team_id].append(p)

        for members in teams.values():
            factor = _VICTORY_POINTS_FACTORS.get(len(members))
            if factor is None:
                continue  # coalition bigger than the known table — falls through below
            if sum(p.victory_points for p in members) >= victory_points_modifier * factor:
                return [p.player_id for p in members]

    # Nobody met a real threshold — either victory_points_modifier is unknown, or the
    # coalition is bigger than the known table covers, or the game was ended by admin/vote
    # with no clear winner. Guess from relative standing as a last resort.
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
