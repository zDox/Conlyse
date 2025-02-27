from __future__ import annotations

from datetime import datetime
from typing import Union

from conflict_interface.data_types.custom_types import ArrayList, Vector
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass

from conflict_interface.data_types.newspaper_state.article import Article
from conflict_interface.data_types.newspaper_state.ranking import Ranking
from conflict_interface.data_types.newspaper_state.report_article import ReportArticle
from conflict_interface.data_types.newspaper_state.statistics_article import StatisticsArticle


@dataclass
class NewspaperState(GameObject):
    C = "ultshared.UltNewspaperState"
    STATE_ID = 2
    articles: Vector[Union[Article,StatisticsArticle]]

    state_type: int  # should be the same as STATE_ID
    time_stamp: datetime
    state_id: str  # Is not the STATE_ID above

    day: int
    ranking: Ranking

    report_articles: ReportArticle

    MAPPING = {
        "articles": "articles",
        "state_type": "stateType",
        "time_stamp": "timeStamp",
        "state_id": "stateID",
        "day": "day",
        "ranking": "ranking",
        "report_articles": "reportArticles",
    }