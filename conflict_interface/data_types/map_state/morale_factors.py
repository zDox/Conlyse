from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject

@dataclass
class MoraleFactors(GameObject):
    C = "mf"
    base_target_morale: int
    max_morale: int
    day_distance: Optional[float]
    building_influence: Optional[HashMap[str, int]]

    MAPPING = {
        "base_target_morale": "baseTargetMorale",
        "max_morale": "maxMorale",
        "day_distance": "dayDistance",
        "building_influence": "buildingInfluence",
    }