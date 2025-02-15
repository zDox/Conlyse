from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils import GameObject

from dataclasses import dataclass

from .article import Article


@dataclass
class NewspaperState(GameObject):
    STATE_ID = 2
    articles: dict[int, Article]

    @classmethod
    def from_dict(cls, obj, game: GameInterface = None):
        articles = {article["messageUID"]: Article.from_dict(article)
                    for article in obj["articles"][1]}
        instance = cls(**{
            "articles": articles,
        })
        instance.game = game
        return instance
