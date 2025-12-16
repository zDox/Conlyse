from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class ResearchRequirementConfig(GameObject):
    C = "ultshared.modding.configuration.UltResearchRequirementConfig"
    expression: str

    MAPPING = {
        "expression": "expression"
    }