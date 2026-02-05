from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.data_types.custom_types import LinkedHashMap
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class MissionReward(GameObject):
    C = "ultshared.modding.configuration.missions.UltMissionReward"
    name: str
    parameters: LinkedHashMap[str, str]
    icon: str

    MAPPING = {
        "name": "name",
        "parameters": "parameters",
        "icon": "icon"

    }