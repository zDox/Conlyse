from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import TreeMap


@dataclass
class RankCache(GameObject):
    C = "ultshared.UltRankCache"
    min_points_to_level: TreeMap[int, int]

    MAPPING = {
        "min_points_to_level": "minPointsToLevel",
    }