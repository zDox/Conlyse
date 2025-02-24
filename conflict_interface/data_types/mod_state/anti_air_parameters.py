from conflict_interface.utils import GameObject
from dataclasses import dataclass
from datetime import datetime

from conflict_interface.utils import \
        unixtimestamp_to_datetime, ConMapping


@dataclass
class AntiAirParameters(GameObject):
    """
    Parameters which describe when the unit will perform the next
    anti-air attack, when the last anti attack was and what the
    distance to the last anti-air attack enemy was.
    """
    next_anti_air_attack: datetime
    last_anti_air_attack: datetime
    last_anti_air_attack_distance: float

    MAPPING = {
        "next_anti_air_attack": "naa",
        "last_anti_air_attack": "laa",
        "last_anti_air_attack_distance": "laadist",
    }
