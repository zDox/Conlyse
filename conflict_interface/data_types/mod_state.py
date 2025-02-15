from conflict_interface.utils import GameObject, MappedValue
from dataclasses import dataclass
from pprint import pprint

from .upgrades import UpgradeType


@dataclass
class ModState(GameObject):
    STATE_ID = 11
    upgrades: dict[int, UpgradeType]
    # unit_types: list(UnitType)
    # research_types: list(ResearchType)
    MAPPING = {
        "upgrades": MappedValue("upgrades", function=lambda obj: {int(upgrade_id): UpgradeType.from_dict(upgrade)
                                                                  for upgrade_id, upgrade
                                                                  in list(obj.items())[1:]})
    }
