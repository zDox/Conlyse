from datetime import datetime


from conflict_interface.data_types.research_state.research_action import ResearchAction
from conflict_interface.data_types.custom_types import ArrayList, HashMap
from conflict_interface.data_types.game_object import GameObject


from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class Research(GameObject):
    C = "ultshared.UltResearch"
    research_type_id: int
    start_time: datetime
    end_time: datetime
    speed_up: int

    MAPPING = {"research_type_id": "researchTypeID",
                "start_time": "startTime",
                "end_time": "endTime",
                "speed_up": "speedUp"}

    def remaining_time(self):
        return self.end_time - self.game.client_time()

    def do_research(self, research_id: int):
        return self.game.game_api.request_game_state_action(ResearchAction(
            research_id=research_id,
        ).to_dict())


@dataclass
class ResearchState(State):
    C = "ultshared.UltResearchState"
    STATE_TYPE = 23
    current_researches: ArrayList[Research]
    completed_researches: HashMap[int, Research]

    # TODO: unlockedMaxLevels, unlockedItems
    research_slots: int

    MAPPING = {"research_slots": "researchSlots",
               "current_researches": "currentResearches",
               "completed_researches": "completedResearches"}