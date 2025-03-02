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