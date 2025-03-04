from itertools import count
from typing import Optional

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.research_state.research_action import ResearchAction
from conflict_interface.data_types.custom_types import ArrayList, HashMap
from conflict_interface.data_types.game_object import GameObject


from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class Research(GameObject):
    C = "ultshared.research.UltResearch"
    research_type_id: int
    start_time: DateTimeMillisecondsInt
    end_time: DateTimeMillisecondsInt
    speed_up: int

    MAPPING = {"research_type_id": "researchTypeID",
                "start_time": "startTime",
                "end_time": "endTime",
                "speed_up": "speedUp",
}


@dataclass
class ResearchState(State):
    C = "ultshared.UltResearchState"
    STATE_TYPE = 23
    current_researches: ArrayList[Research]
    completed_researches: HashMap[int, Research]

    unlocked_max_levels: Optional[HashMap[int, int]]  # TODO check type
    unlocked_items: HashMap[int, int]  # TODO check type

    research_slots: int

    MAPPING = {"research_slots": "researchSlots",
               "current_researches": "currentResearches",
               "completed_researches": "completedResearches",
               "unlocked_max_levels": "unlockedMaxLevels",
               "unlocked_items": "unlockedItems",
    }

    def empty_slots(self) -> int:
        return sum(slot is None for slot in self.current_researches)

    def has_completed_research(self, research_id: int) -> bool:
        return any(research.research_type_id == research_id for research in self.completed_researches.values())

    def is_researchable(self, research_id: int) -> bool:
        # TODO check if has necessary resources
        research_type = self.game.get_research_type(research_id)

        if self.empty_slots() == 0:
            return False
        elif any(research.research_type_id == research_id for research in self.completed_researches.values()):
            return False

        if all(self.has_completed_research(required_research_id) for required_research_id in research_type.required_researches.keys()):
            return True
        else:
            return False