from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
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