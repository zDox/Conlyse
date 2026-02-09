from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class ResearchRequirementConfig(GameObject):
    C = "ultshared.modding.configuration.UltResearchRequirementConfig"
    expression: str

    MAPPING = {
        "expression": "expression"
    }