from dataclasses import dataclass

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade
from conflict_interface.data_types.game_object import GameObject


@dataclass
class ProvinceProduction(GameObject):
    C = "ultshared.UltProvinceProduction"
    upgrade: ModableUpgrade
    time: DateTimeMillisecondsInt
    start_time: DateTimeMillisecondsInt
    builder_id: int = -1

    MAPPING = {
        "upgrade": "u",
        "time": "t",
        "start_time": "s",
        "builder_id": "b",
    }
