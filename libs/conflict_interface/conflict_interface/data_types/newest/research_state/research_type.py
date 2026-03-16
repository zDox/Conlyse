from dataclasses import dataclass
from typing import Optional

from ..custom_types import HashMap
from ..custom_types import TimeDeltaSecondsInt
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..mod_state.configuration import ConflictCondition
from ..mod_state.configuration import FactionSpecificConfig
from ..research_state.faction_specific_research_config import FactionSpecificResearchConfig
from ..research_state.research_action_result import ResearchActionResult
from ..resource_state.resource_state_enums import ResourceType

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class ResearchType(GameObject):
    C = "ultshared.research.UltResearchType"
    item_id: int
    identifier: str # Icon identifier for Research Icons
    set: int # Tab ID infantry = 1
    set_order_id: int # Order in Tab ID ( ID for one research line)
    costs: HashMap[ResourceType, float]
    build_time: TimeDeltaSecondsInt
    day_available: int
    replaced_research: int
    required_researches: HashMap[int, float]
    required_plans: HashMap[int, int] # TODO Check int int
    tracking_option_id: int
    unlocked_items: HashMap[int, int] # TODO -||-
    unlocked_max_level: HashMap[int, int] # TODO -||-
    name: str
    name_faction1: str
    name_faction2: str
    name_faction3: str
    name_faction4: str
    research_requirement_config: ConflictCondition
    description: str
    faction_specific_research_config: Optional[FactionSpecificResearchConfig]
    faction_specific_config: Optional[FactionSpecificConfig]

    _tier: int = None
    _replacing_research_id: int = None
    MAPPING = {
        "item_id": "itemID",
        "set_order_id": "setOrderID",
        "day_available": "dayAvailable",
        "replaced_research": "replacedResearch",
        "tracking_option_id": "trackingOptionID",
        "name_faction1": "nameFaction1",
        "name_faction2": "nameFaction2",
        "name_faction3": "nameFaction3",
        "name_faction4": "nameFaction4",
        "research_requirement_config": "researchRequirementConfig",
        "faction_specific_research_config": "factionSpecificResearchConfig",
        "unlocked_items": "unlockedItems",
        "unlocked_max_level": "unlockedMaxLevel",
        "required_researches": "requiredResearches",
        "required_plans": "requiredPlans",
        "build_time": "buildTime",
        "name": "name",
        "description": "desc",
        "set": "set",
        "identifier": "identifier",
        "costs": "costs",
        "faction_specific_config": "factionSpecificConfig",
    }

    @property
    def tier(self):
        """
        Get the tier of the research type. The tier is incremented based on the replaced research.
        If no replaced research exists and it can still be replaced, tier is 1.
        Otherwise, tier is 0.
        """
        if not self._tier:
            replaced_research_id = self.get_replaced_research()
            if replaced_research_id > 0:
                replaced_research = self.game.get_research_type(replaced_research_id)
                if replaced_research:
                    self._tier = replaced_research.tier + 1
                else:
                    self._tier = 0
                    raise ValueError(
                        f"Expected research {replaced_research_id} does not exist in the current mod.")
            else:
                self._tier = 1 if self.can_be_replaced() else 0

        return self._tier

    def can_be_replaced(self):
        """
        Check if the research can be replaced by another research.
        """
        return self.get_replacing_research() > 0

    def get_replacing_research(self):
        """
        Determine the research that is replacing this research.
        """
        if self._replacing_research_id is None:
            # Mocking a mod call or similar lookup process for replacing research
            research_types = self.game.game_state.states.mod_state.research_types
            self._replacing_research_id = next(
                (research.item_id for research in research_types.values()
                 if research.get_replaced_research() == self.item_id),
                None  # Default to None if no match is found
            )
        return self._replacing_research_id or 0

    def get_replaced_research(self):
        """
        Get the research that this research replaces.
        """
        return self.replaced_research


    def has_tiers(self):
        """
        Checks whether the research has tiers.
        """
        return self.tier >= 1

    def get_max_tier(self):
        """
        Get the maximum tier possible for this research type.
        """
        replacing_research = self.get_replacing_research_item()
        return replacing_research.get_max_tier() if replacing_research else self.tier

    def get_replacing_research_item(self):
        """
        Get the research item replacing this research.
        """
        replacing_research_id = self.get_replacing_research()
        return self.game.game_state.states.mod_state.research_types.get(replacing_research_id)

    def research(self) -> tuple[int | None, ResearchActionResult]:
        """
        Researches the current research type. Use the method in ResearchState to perform the action.

        Returns:
            tuple[int | None, ResearchActionResult]: A tuple containing the result of the
            research operation. The first element is a unique action id. The second
            element is an instance of ResearchActionResult providing additional details about
            the research action.
        """
        return self.game.game_state.states.research_state.research(self.item_id)

    def cancel_research(self) -> tuple[int | None, ResearchActionResult]:
        """
        Cancels the research for the current research type.
        Use the method in ResearchState to perform the action.

        Returns
        -------
        tuple[int | None, ResearchActionResult]
            A tuple containing the unique action id if a research action will/was performed and
            the Result of the ResearchAction.
        """
        return self.game.game_state.states.research_state.cancel_research(self.item_id)