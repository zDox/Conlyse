from dataclasses import dataclass

from .article import Article


@dataclass
class NewspaperState:
    STATE_ID = 2
    articles: dict[int, Article]

    @classmethod
    def from_dict(cls, obj):
        articles = {article["messageUID"]: Article.from_dict(article)
                    for article in obj["articles"][1]}
        return cls(**{
            "articles": articles
        })
