from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import LinkedHashMap


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
