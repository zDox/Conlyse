from conflict_interface.utils import GameObject
from dataclasses import dataclass
from datetime import datetime

from conflict_interface.utils import \
        unixtimestamp_to_datetime, ConMapping


@dataclass
class AntiAirParameters(GameObject):
    next_anti_air_attack: datetime
    last_anti_air_attack: datetime
    last_anti_air_attack_distance: float

    MAPPING = {
        "next_anti_air_attack": "naa",
        "last_anti_air_attack": "laa",
        "last_anti_air_attack_distance": "laadist",
    }
