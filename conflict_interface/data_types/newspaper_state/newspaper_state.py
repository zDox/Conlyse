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
from conflict_interface.data_types.state import State


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