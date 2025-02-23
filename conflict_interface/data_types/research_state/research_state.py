from conflict_interface.utils import GameObject

from dataclasses import dataclass

@dataclass
class ResearchState(GameObject):
    STATE_ID = 23
    # current_researches: list(Research)
    # completed_researches: list(Research)
    research_slots: int
    MAPPING = {"research_slots": "researchSlots"}


    print("HI")