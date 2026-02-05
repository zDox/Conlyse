from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.data_types.custom_types import HashSet
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable
from conflict_interface.data_types.player_state.faction import Faction

from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class FactionSpecificResearchConfig(GameObject):
    C = "ultshared.modding.configuration.UltFactionSpecificResearchConfig"
    factions: HashSet[Faction]

    MAPPING = {
        "factions": "factions"
    }
