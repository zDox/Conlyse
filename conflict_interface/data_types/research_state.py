from datetime import datetime

from conflict_interface.utils import GameObject, ArrayList, HashMap

from dataclasses import dataclass

@dataclass
class Research(GameObject):
    research_type_id: int
    start_time: datetime
    end_time: datetime
    speed_up: int

    MAPPING = {"research_type_id": "researchTypeId",
                "start_time": "startTime",
                "end_time": "endTime",
                "speed_up": "speedUp"}

    def remaining_time(self):
        return self.end_time - self.game.client_time();

@dataclass
class ResearchState(GameObject):
    STATE_ID = 23
    current_researches: ArrayList[Research]
    completed_researches: HashMap[int, Research]

    # TODO: unlockedMaxLevels, unlockedItems
    research_slots: int

    MAPPING = {"research_slots": "researchSlots",
               "current_researches": "currentResearches",
               "completed_researches": "completedResearches"}

