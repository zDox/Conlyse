from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.data_types.custom_types import TreeMap
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class RankCache(GameObject):
    C = "ultshared.UltRankCache"
    min_points_to_level: TreeMap[int, int]

    MAPPING = {
        "min_points_to_level": "minPointsToRankLevel",
    }