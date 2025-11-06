from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import LinkedHashMap


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