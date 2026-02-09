from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..mod_state.mod_state_enums import DamageType

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class Boost(GameObject):
    C = "ultshared.modding.configuration.UltArmyBoostConfig$Boost"
    stat: str # TODO is an enum
    bonus: float
    damage_type: DamageType

    MAPPING = {
        "stat": "stat",
        "bonus": "bonus",
        "damage_type": "damageType",
    }

    __hash__ = GameObject.__hash__