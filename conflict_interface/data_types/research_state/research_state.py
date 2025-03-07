from itertools import count
from typing import Optional

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.research_state.research_action import ResearchAction
from conflict_interface.data_types.custom_types import ArrayList, HashMap
from conflict_interface.data_types.game_object import GameObject


from dataclasses import dataclass

from conflict_interface.data_types.research_state.research_action import ResearchActionResult
from conflict_interface.data_types.state import State
from conflict_interface.utils.exceptions import ActionException


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
        """
        Returns the number of empty research slots.
        """
        if len(self.current_researches) == 2:
            return sum(slot is None for slot in self.current_researches)
        else:
            return 2 - len(self.current_researches)

    def has_completed_research(self, research_id: int) -> bool:
        """
        Returns if the research has already been completed.
        """
        return any(research.research_type_id == research_id for research in self.completed_researches.values())

    def get_researchability(self, research_id: int) -> ResearchActionResult:
        """
        Determines the researchability of a specific research based on its ID.

        Evaluates if the given research can be undertaken depending on the availability of
        research slots, completion status of the research, and whether the required
        prerequisite researches have been completed.

        Arguments:
            research_id (int): The unique identifier of the research to evaluate.

        Returns:
            ResearchActionResult: An enumeration indicating the research's researchability.
        """
        research_type = self.game.get_research_type(research_id)
        # TODO check if has necessary resources

        if self.empty_slots() == 0:
            return ResearchActionResult.FullResearchSlots
        elif any(research.research_type_id == research_id for research in self.completed_researches.values()):
            return ResearchActionResult.AlreadyCompleted

        elif any(not self.has_completed_research(required_research_id) for required_research_id in research_type.required_researches.keys()):
            return ResearchActionResult.InsufficientRequirements
        return ResearchActionResult.Ok

    def is_researchable(self, research_id: int) -> bool:
        """
        Determines if a research action with the provided research ID is researchable or
        not.

        Args:
            research_id (int): The ID of the research action to be checked.

        Returns:
            bool: True if the research is considered researchable; False otherwise.
        """
        return self.get_researchability(research_id) == ResearchActionResult.Ok

    def research(self, research_id: int) -> tuple[Optional[int], ResearchActionResult]:
        """
        Determines if a research action can be performed for the given research_id and executes it if possible.
        If the research action is not executable, indicates the researchability status.

        Args:
            research_id (int): The identifier of the research which should be researched.

        Returns:
            tuple[Optional[int], ResearchActionResult]:
            A tuple consisting of the unique action id or None (if research is not
            performed), and the result of the research attempt (researchability state).
        """
        if self.is_researchable(research_id):
            return self.game.do_action(ResearchAction(research_id, cancel=False)), ResearchActionResult.Ok
        else:
            return None, self.get_researchability(research_id)

    def is_researching(self, research_id: int) -> bool:
        """
        Determines if the specified research ID is currently being researched.

        Args:
            research_id (int): The unique identifier of the research to check.

        Returns:
            bool: True if the specified research ID is found in the current research items, otherwise False.
        """
        return any(research.research_type_id == research_id for research in self.current_researches)


    def cancel_research(self, research_id: int) -> tuple[Optional[int], ResearchActionResult]:
        """
        Cancels an ongoing research process for the specified research ID.

        If the specified research ID corresponds to a
        currently active research, the cancellation action will be executed.

        Parameters:
         research_id (int): The unique identifier of the research to cancel.

        Returns:
         tuple[Optional[None], ResearchActionResult]:
         - The first element is the unique action id or None, indicating the cancellation attempt was a failure.
         - The second element is ResearchActionResult, indicating the result of the cancellation attempt.
        """
        if self.is_researching(research_id):
            return self.game.do_action(ResearchAction(research_id, cancel=True)), ResearchActionResult.Ok
        else:
            return None, ResearchActionResult.NotAvailable