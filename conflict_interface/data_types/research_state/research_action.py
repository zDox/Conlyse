from dataclasses import dataclass

from conflict_interface.data_types.action import Action


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
