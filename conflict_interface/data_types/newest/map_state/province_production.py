from dataclasses import dataclass
from typing import Union

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.data_types.mod_state.modable_unit import SpecialUnit
from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade
from conflict_interface.game_object.game_object import GameObject

from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class ProvinceProduction(GameObject):
    C = "ultshared.UltProvinceProduction"
    upgrade: Union[ModableUpgrade, SpecialUnit]
    time: DateTimeMillisecondsInt
    start_time: DateTimeMillisecondsInt
    builder_id: int = -1

    MAPPING = {
        "upgrade": "u",
        "time": "t",
        "start_time": "s",
        "builder_id": "b",
    }
