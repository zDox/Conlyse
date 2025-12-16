from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
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