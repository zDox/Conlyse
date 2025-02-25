from __future__ import annotations

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass

from conflict_interface.data_types.newspaper_state.article import Article


@dataclass
class NewspaperState(GameObject):
    C = "ultshared.UltNewspaperState"
    STATE_ID = 2
    articles: ArrayList[Article]
    MAPPING = {
        "articles": "articles",
    }