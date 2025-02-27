from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class ResearchAction(GameObject):
    """
    Represents a research action.

    Attributes:

    """
    C = "ultshared.action.UltResearchAction"

    research_id: int
    cancel: bool = False
    MAPPING = {
        "research_id": "researchID",
        "cancel": "cancel"
    }
