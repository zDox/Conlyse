from dataclasses import dataclass
from enum import Enum
from typing import Union

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..mod_state.modable_unit import SpecialUnit
from ..action import Action
from ..custom_types import Vector, DefaultEnumMeta
from ..mod_state.moddable_upgrade import ModableUpgrade

from ..version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
class UpdateProvinceActionModes(Enum, metaclass=DefaultEnumMeta):
    PROVINCE = 0
    UPGRADE = 1 # Building an upgrade in Province
    SPECIAL_UNIT = 2 # Mobilizing a unit in Province
    CANCEL_PRODUCING = 3
    CANCEL_BUILDING = 4
    DEPLOYMENT_TARGET = 5
    DEMOLISH_UPGRADE = 6

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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