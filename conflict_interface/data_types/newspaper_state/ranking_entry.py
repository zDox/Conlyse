from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class RankingEntry(GameObject):
    C = "ultshared.UltRankingEntry"
    id: int
    type: str
    points: int
    percentage: float

    MAPPING = {
        "id": "id",
        "type": "type",
        "points": "points",
        "percentage": "percentage",
    }