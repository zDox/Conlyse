from dataclasses import dataclass
from typing import Union

from ..custom_types import Vector
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..newspaper_state.article import Article
from ..newspaper_state.ranking import Ranking
from ..newspaper_state.report_article import ReportArticle
from ..newspaper_state.statistics_article import StatisticsArticle
from ..state import State
from ..update_helpers import state_update
from ..update_helpers import list_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode


@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class NewspaperState(State):
    C = "ultshared.UltNewspaperState"
    STATE_TYPE = 2
    articles: Vector[Union[Article,StatisticsArticle]]

    day: int
    ranking: Ranking

    report_articles: ReportArticle

    MAPPING = {
        "articles": "articles",
        "day": "day",
        "ranking": "ranking",
        "report_articles": "reportArticles",
    }

    def update(self, other: "NewspaperState", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        # TODO update newspaper to save paper of other dayys
        state_update(self, other, path=path, rp=rp)

        if rp:
            if self.day != other.day:
                rp.replace(path + ["day"], self.day, other.day)
        self.ranking.update(other.ranking, path + ["ranking"], rp)
        self.day = other.day
        list_update(self.articles, other.articles, path + ["articles"], rp)
