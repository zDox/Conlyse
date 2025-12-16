from dataclasses import dataclass
from enum import Enum
from typing import Union

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable
from conflict_interface.data_types.mod_state.modable_unit import SpecialUnit
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.custom_types import Vector, DefaultEnumMeta
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade

@binary_serializable(SerializationCategory.ENUM)
class UpdateProvinceActionModes(Enum, metaclass=DefaultEnumMeta):
    PROVINCE = 0
    UPGRADE = 1 # Building an upgrade in Province
    SPECIAL_UNIT = 2 # Mobilizing a unit in Province
    CANCEL_PRODUCING = 3
    CANCEL_BUILDING = 4
    DEPLOYMENT_TARGET = 5
    DEMOLISH_UPGRADE = 6

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class UpdateProvinceAction(Action):
    C = "ultshared.action.UltUpdateProvinceAction"
    province_ids: Vector[int]
    mode: UpdateProvinceActionModes
    upgrade: Union[ModableUpgrade, SpecialUnit] = None
    slot: int = 0

    MAPPING = {
        "province_ids": "provinceIDs",
        "mode": "mode",
        "slot": "slot",
        "upgrade": "upgrade",
    }