
from dataclasses import dataclass

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class AntiAirParameters(GameObject):
    """
    Parameters which describe when the unit will perform the next
    anti-air attack, when the last anti attack was and what the
    distance to the last anti-air attack enemy was.
    """
    C = "ultshared.UltAntiAirParameters"
    next_anti_air_attack: DateTimeMillisecondsInt
    last_anti_air_attack: DateTimeMillisecondsInt
    last_anti_air_attack_distance: float

    MAPPING = {
        "next_anti_air_attack": "naa",
        "last_anti_air_attack": "laa",
        "last_anti_air_attack_distance": "laadist",
    }
