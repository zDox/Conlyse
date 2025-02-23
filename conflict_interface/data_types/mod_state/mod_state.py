from conflict_interface.utils import GameObject, HashMap
from dataclasses import dataclass
from pprint import pprint

from .upgrade import UpgradeType
from .unit_type import UnitType


@dataclass
class ModState(GameObject):
    STATE_ID = 11
    upgrades: HashMap[int, UpgradeType]
    unit_types: HashMap[int, UnitType]
    # research_types: list(ResearchType)
    MAPPING = {
        "upgrades": "upgrades",
        "unit_types": "unitTypes"
    }