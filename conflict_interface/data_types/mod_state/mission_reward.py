from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import LinkedHashMap


@dataclass
class MissionReward(GameObject):
    C = "ultshared.modding.types.UltMissionReward"
    name: str
    parameters: LinkedHashMap[int, int]
    icon: str