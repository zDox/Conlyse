from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.mod_state.mod_state_enums import DamageType


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