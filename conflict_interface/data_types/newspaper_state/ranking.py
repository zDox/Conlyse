from dataclasses import dataclass

from ..custom_types import HashMap # TODO why is tis relative needed
from ..game_object import GameObject


@dataclass
class Ranking(GameObject):
    C = "ultshared.UltRanking"
    winner: int
    ranking: list[int]
    players_rank_sorted: list[int]
    winner_team: int
    team_ranking: HashMap[int, int]
    teams_rank_sorted: list[int]
    initialized: bool

    MAPPING = {
        "winner": "winner",
        "ranking": "ranking",
        "players_rank_sorted": "playersRankSorted",
        "winner_team": "winnerTeam",
        "team_ranking": "teamRanking",
        "teams_rank_sorted": "teamsRankSorted",
        "initialized": "initialized",
    }