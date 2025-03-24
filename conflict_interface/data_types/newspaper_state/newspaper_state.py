from dataclasses import dataclass
from dataclasses import field
from typing import Union

from conflict_interface.data_types.custom_types import Vector
from conflict_interface.data_types.newspaper_state.article import Article
from conflict_interface.data_types.newspaper_state.ranking import Ranking
from conflict_interface.data_types.newspaper_state.report_article import ReportArticle
from conflict_interface.data_types.newspaper_state.statistics_article import StatisticsArticle
from conflict_interface.data_types.state import State
from conflict_interface.data_types.state import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode


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
            if self.articles != other.articles:
                rp.replace(path + ["articles"], self.articles, other.articles)
        self.day = other.day
        self.articles = other.articles