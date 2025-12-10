from dataclasses import dataclass
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


def list_update(original: list, other: list, path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
    min_length = min(len(original), len(other))
    for i in range(min_length):
        if original[i] != other[i]:
            if type(original[i]) == type(other[i]) and hasattr(original[i], "update"):
                original[i].update(other[i], path + [i], rp)
            else:
                if rp:
                    rp.replace(path + [i], original[i], other[i])
                original[i] = other[i]
    if len(other) > len(original):
        for i in range(len(original), len(other)):
            if rp:
                rp.add(path + [i], None, other[i])
            original.append(other[i])
    elif len(original) > len(other):
        for i in range(len(original)-1, len(other)-1, -1):
            if rp:
                rp.remove(path + [i], original[i])
            original.pop(i)

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
        self.day = other.day
        list_update(self.articles, other.articles, path + ["articles"], rp)
