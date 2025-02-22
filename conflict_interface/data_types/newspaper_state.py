from __future__ import annotations
from typing import TYPE_CHECKING

from ..utils.json_mapped_class import ArrayList

if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils import GameObject

from dataclasses import dataclass

from .article import Article


@dataclass
class NewspaperState(GameObject):
    STATE_ID = 2
    articles: ArrayList[Article]
    MAPPING = {
        "articles": "articles",
    }