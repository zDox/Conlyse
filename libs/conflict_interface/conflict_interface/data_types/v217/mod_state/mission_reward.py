from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from ..custom_types import LinkedHashMap
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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