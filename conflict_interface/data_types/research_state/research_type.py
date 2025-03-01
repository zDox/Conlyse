from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.research_state.faction_specific_research_config import FactionSpecificResearchConfig
from conflict_interface.data_types.research_state.research_requirement_config import ResearchRequirementConfig


@dataclass
class ResearchType(GameObject):
    C = "ultshared.research.UltResearchType"
    item_id: int
    identifier: str
    set: int
    set_order_id: int
    costs: HashMap[int, int]
    build_time: int
    day_available: int
    replaced_research: int
    required_researches: HashMap[int, int]
    required_plans: HashMap[int, int] # TODO Check int int
    tracking_option_id: int
    unlocked_items: HashMap[int, int] # TODO -||-
    unlocked_max_level: HashMap[int, int] # TODO -||-
    name: str
    name_faction1: str
    name_faction2: str
    name_faction3: str
    name_faction4: str
    research_requirement_config: ResearchRequirementConfig
    description: str
    faction_specific_research_config: Optional[FactionSpecificResearchConfig]

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
    }