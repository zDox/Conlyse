from dataclasses import dataclass

from conflict_interface.data_types.action import Action
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
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
