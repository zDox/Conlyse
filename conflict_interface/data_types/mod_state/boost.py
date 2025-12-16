from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable
from conflict_interface.data_types.mod_state.mod_state_enums import DamageType

@binary_serializable(SerializationCategory.DATACLASS)
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