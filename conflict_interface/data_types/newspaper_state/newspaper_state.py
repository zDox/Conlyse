from __future__ import annotations
from typing import TYPE_CHECKING

from conflict_interface.utils.json_mapped_class import ArrayList

if TYPE_CHECKING:
    pass
from conflict_interface.utils import GameObject

from dataclasses import dataclass

from conflict_interface.data_types.newspaper_state.article import Article


@dataclass
class NewspaperState(GameObject):
    STATE_ID = 2
    articles: ArrayList[Article]
    MAPPING = {
        "articles": "articles",
    }