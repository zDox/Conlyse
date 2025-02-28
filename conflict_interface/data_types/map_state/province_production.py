from dataclasses import dataclass

from conflict_interface.data_types.mod_state import ModableUpgrade
from conflict_interface.data_types.game_object import GameObject


@dataclass
class ProvinceProduction(GameObject):
    C = "ultshared.UltProvinceProduction"
    upgrade: ModableUpgrade
    time: int
    start_time: int
    builder_id: int = -1

    MAPPING = {
        "upgrade": "u",
        "time": "t",
        "start_time": "s",
        "builder_id": "b",
    }
