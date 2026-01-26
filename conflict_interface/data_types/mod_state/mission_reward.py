from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import LinkedHashMap
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
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