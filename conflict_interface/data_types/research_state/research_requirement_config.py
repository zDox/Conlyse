from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class ResearchRequirementConfig(GameObject):
    C = "ultshared.modding.configuration.UltResearchRequirementConfig"
    expression: str

    MAPPING = {
        "expression": "expression"
    }