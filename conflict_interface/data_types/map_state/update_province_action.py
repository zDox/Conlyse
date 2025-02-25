from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.custom_types import Vector
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.mod_state import ModableUpgrade
from conflict_interface.utils import GameObject, Vector


class UpdateProvinceActionModes(Enum, metaclass=DefaultEnumMeta):
    PROVINCE = 0
    UPGRADE = 1 # Building an upgrade in Province
    SPECIAL_UNIT = 2
    CANCEL_PRODUCING = 3
    CANCEL_BUILDING = 4
    DEPLOYMENT_TARGET = 5
    DEMOLISH_UPGRADE = 6

@dataclass
class UpdateProvinceAction(GameObject):
    C = "ultshared.action.UltUpdateProvinceAction"
    province_ids: Vector[int]
    mode: UpdateProvinceActionModes
    upgrade: ModableUpgrade
    slot: int = 0

    C = "ultshared.action.UltUpdateProvinceAction"
    MAPPING = {
        "province_ids": "provinceIDs",
        "mode": "mode",
        "slot": "slot",
        "upgrade": "upgrade",
    }
# TODO Remove
    def __init__(self, province_ids, mode, slot, upgrade=None, game=None):
        super().__init__(game)
        self.province_ids = province_ids
        self.mode = mode
        self.slot = slot
        self.upgrade = upgrade