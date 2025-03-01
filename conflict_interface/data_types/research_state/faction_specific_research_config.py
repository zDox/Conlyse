from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import HashSet


@dataclass
class FactionSpecificResearchConfig(GameObject):
    C = "ultshared.modding.configuration.UltFactionSpecificResearchConfig"
    factions: HashSet[int]

    MAPPING = {
        "factions": "factions"
    }
