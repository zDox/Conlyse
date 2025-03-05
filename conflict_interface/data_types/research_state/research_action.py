from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.action import Action
from conflict_interface.data_types.game_object import GameObject


class ResearchActionResult(Enum):
    Ok = 0
    FullResearchSlots = 1
    AlreadyCompleted = 2
    InsufficientRequirements = 3


@dataclass
class ResearchAction(Action):
    """
    Represents a research action.
    Attributes:
        research_id (int): The identifier of the research type
        cancel (bool): Whether the research action should be cancelled
    """
    C = "ultshared.action.UltResearchAction"

    research_id: int
    cancel: bool = False
    MAPPING = {
        "research_id": "researchID",
        "cancel": "cancel"
    }
