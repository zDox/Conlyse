

from dataclasses import dataclass

@dataclass
class ResearchState:
    STATE_ID = 23
    # current_researches: list(Research)
    # completed_researches: list(Research)
    research_slots: int
