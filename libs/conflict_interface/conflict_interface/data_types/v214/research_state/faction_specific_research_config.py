from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from ..custom_types import HashSet
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..player_state.faction import Faction

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class FactionSpecificResearchConfig(GameObject):
    C = "ultshared.modding.configuration.UltFactionSpecificResearchConfig"
    factions: HashSet[Faction]

    MAPPING = {
        "factions": "factions"
    }
