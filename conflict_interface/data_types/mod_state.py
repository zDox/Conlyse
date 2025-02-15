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

    @classmethod
    def from_dict(cls, obj: dict, game = None):
        upgrades = {int(upgrade_id): UpgradeType.from_dict(upgrade, game=game)
         for upgrade_id, upgrade
         in list(obj["upgrades"].items())[1:]}
        instance = cls(upgrades=upgrades)
        instance.game = game
        return instance
