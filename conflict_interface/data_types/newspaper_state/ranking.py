from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import RankingEntryList
from conflict_interface.data_types.decorators import binary_serializable
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.newspaper_state.ranking_entry import RankingEntry
from conflict_interface.data_types.update_helpers import dict_update
from conflict_interface.data_types.update_helpers import list_update
from conflict_interface.replay.constants import PathNode
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch


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

    def update(self, other: "Ranking", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        if rp is not None:
            if self.winner != other.winner:
                rp.replace(path + ["winner"], self.winner, other.winner)
            if self.winner_team != other.winner_team:
                rp.replace(path+["winner_team"], self.winner_team, other.winner_team)
            if self.initialized != other.initialized:
                rp.replace(path+["initialized"], self.initialized, other.initialized)

        self.winner = other.winner
        self.winner_team = other.winner_team
        self.initialized = other.initialized

        list_update(self.ranking, other.ranking, path + ["ranking"], rp)
        list_update(self.players_rank_sorted, other.players_rank_sorted, path + ["players_rank_sorted"], rp)
        list_update(self.teams_rank_sorted, other.teams_rank_sorted, path + ["teams_rank_sorted"], rp)
        list_update(self.unified_rank_sorted, other.unified_rank_sorted, path + ["unified_rank_sorted"], rp)
        dict_update(self.team_ranking, other.team_ranking, path+ ["team_ranking"], rp)
