from dataclasses import dataclass
from typing import Optional

from .ranking_entry import RankingEntry
from ..custom_types import HashMap # TODO why is tis relative needed
from ..custom_types import RankingEntryList
from ..game_object import GameObject
from ..game_object_binary import SerializationCategory
from ..game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class Ranking(GameObject):
    C = "ultshared.UltRanking"
    winner: int
    ranking: list[int]
    players_rank_sorted: Optional[list[int]]
    winner_team: int
    team_ranking: HashMap[int, int]
    teams_rank_sorted: Optional[list[int]]
    initialized: bool
    unified_rank_sorted: Optional[RankingEntryList[RankingEntry]]

    MAPPING = {
        "winner": "winner",
        "ranking": "ranking",
        "players_rank_sorted": "playersRankSorted",
        "winner_team": "winnerTeam",
        "team_ranking": "teamRanking",
        "teams_rank_sorted": "teamsRankSorted",
        "initialized": "initialized",
        "unified_rank_sorted": "unifiedRankSorted",
    }