from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class MoraleFactors(GameObject):
    C = "mf"
    base_target_morale: int
    max_morale: int
    day_distance: Optional[float]
    building_influence: Optional[HashMap[str, int]]
    war_countries: Optional[int]
    war_influence: Optional[int]
    capital_distance_influence: Optional[int]
    neighbour_influence: Optional[int]
    enemy_neighbour_influence: Optional[int]

    MAPPING = {
        "base_target_morale": "baseTargetMorale",
        "max_morale": "maxMorale",
        "day_distance": "dayDistance",
        "building_influence": "buildingInfluence",
        "war_countries": "warCountries",
        "war_influence": "warInfluence",
        "capital_distance_influence": "capitalDistanceInfluence",
        "neighbour_influence": "neighbourInfluence",
        "enemy_neighbour_influence": "enemyNeighbourInfluence",
    }