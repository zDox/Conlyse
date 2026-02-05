from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.data_types.custom_types import LinkedHashMap
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class MissionTrigger(GameObject):
    C = "ultshared.modding.configuration.missions.UltMissionTrigger"

    client_trigger: bool
    parameter: LinkedHashMap[str, str]
    name: str

    MAPPING = {
        "client_trigger": "clientTrigger",
        "parameter": "params",
        "name": "name"
    }
