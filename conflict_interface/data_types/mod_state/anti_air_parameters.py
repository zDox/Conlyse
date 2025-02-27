
from dataclasses import dataclass
from datetime import datetime

from conflict_interface.data_types.game_object import GameObject


@dataclass
class AntiAirParameters(GameObject):
    """
    Parameters which describe when the unit will perform the next
    anti-air attack, when the last anti attack was and what the
    distance to the last anti-air attack enemy was.
    """
    C = "ultshared.UltAntiAirParameters"
    next_anti_air_attack: datetime
    last_anti_air_attack: datetime
    last_anti_air_attack_distance: float

    MAPPING = {
        "next_anti_air_attack": "naa",
        "last_anti_air_attack": "laa",
        "last_anti_air_attack_distance": "laadist",
    }
