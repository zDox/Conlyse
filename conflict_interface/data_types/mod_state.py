from conflict_interface.utils import GameObject, ConMapping
from dataclasses import dataclass
from pprint import pprint

from .upgrades import UpgradeType
from .warfare import UnitType


@dataclass
class ModState(GameObject):
    STATE_ID = 11
    upgrades: dict[int, UpgradeType]
    unit_types: dict[int, UnitType]
    # research_types: list(ResearchType)

    @classmethod
    def from_dict(cls, obj: dict, game = None):
        upgrades = {int(upgrade_id): UpgradeType.from_dict(upgrade, game=game)
         for upgrade_id, upgrade
         in list(obj["upgrades"].items())[1:]}
        unit_types = {int(unit_id): UnitType.from_dict(unit, game=game)
                    for unit_id, unit
                    in list(obj["unitTypes"].items())[1:]}
        instance = cls(upgrades=upgrades, unit_types=unit_types)
        instance.game = game
        return instance
