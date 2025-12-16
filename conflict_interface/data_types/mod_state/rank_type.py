from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class RankType(GameObject):
    C = "ultshared.modding.types.UltRankType"
    item_id: int
    officer: bool
    min_points: int

    MAPPING = {
        "item_id": "itemID",
        "officer": "officer",
        "min_points": "minPoints",
    }