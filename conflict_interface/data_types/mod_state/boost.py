from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable
from conflict_interface.data_types.mod_state.mod_state_enums import DamageType

from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
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