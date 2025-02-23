from dataclasses import dataclass

from conflict_interface.data_types.mod_state import ModableUpgrade, SpecialUnit
from conflict_interface.utils import GameObject, LinkedList, ArrayList


@dataclass
class ProvinceProperty(GameObject):
    possible_upgrades: LinkedList[ModableUpgrade]
    queueable_upgrades: LinkedList[ModableUpgrade]

    possible_productions: ArrayList[SpecialUnit]
    queueable_productions: ArrayList[SpecialUnit]

    revolt_chance: int
    uprising_chance: int
    target_morale: int

    MAPPING = {
        "possible_upgrades": "possibleUpgrades",
        "queueable_upgrades": "queueableUpgrades",
        "possible_productions": "possibleProductions",
        "queueable_productions": "queueableProductions",
        "revolt_chance": "revoltChance",
        "uprising_chance": "uprisingChance",
        "target_morale": "targetMorale",
    }
