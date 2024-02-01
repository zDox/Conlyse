from dataclasses import dataclass
from datetime import datetime

from conflict_interface.utils import JsonMappedClass, \
        unixtimestamp_to_datetime, MappedValue


@dataclass
class AntiAirParameters(JsonMappedClass):
    next_anti_air_attack: datetime
    last_anti_air_attack: datetime
    last_anti_air_attack_distance: float

    mapping = {
        "next_anti_air_attack": MappedValue("naa", unixtimestamp_to_datetime),
        "last_anti_air_attack": MappedValue("laa", unixtimestamp_to_datetime),
        "last_anti_air_attack_distance": "laadist",
    }
