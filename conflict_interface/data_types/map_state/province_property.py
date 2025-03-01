from dataclasses import dataclass
from typing import Union

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.map_state.morale_factors import MoraleFactors
from conflict_interface.data_types.map_state.revolt_suppression_property import RevoltSuppressionProperty
from conflict_interface.data_types.mod_state import SpecialUnit
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade
from conflict_interface.data_types.custom_types import LinkedList, ArrayList


@dataclass
class ProvinceProperty(GameObject):
    """
    Represents the additional properties of a province in the game.

    This class is only given for a province that is owned by the current player.

    Attributes:
        possible_upgrades: A linked list representing all upgrades that are possible for the province.
        queueable_upgrades: A linked list representing upgrades that can currently be queued for the
                            province.
        possible_productions: An array list of special units that can be potentially produced in the province.
        queueable_productions: An array list of special units that can currently be queued for production in the
                            province.
        revolt_chance: The chance of a revolt happening in the province expressed as a percentage.
        uprising_chance: The chance of an uprising occurring in the province expressed as a percentage.
        target_morale: The morale that will be reached over time.
    """
    C = "ultshared.UltProvinceProperties"
    possible_upgrades: LinkedList[ModableUpgrade]
    queueable_upgrades: LinkedList[ModableUpgrade]

    possible_productions: Union[ArrayList[SpecialUnit], LinkedList[SpecialUnit]]
    queueable_productions: Union[ArrayList[SpecialUnit], LinkedList[SpecialUnit]]

    revolt_chance: int
    uprising_chance: int
    target_morale: int

    base_uprising_chance: float
    morale_factors: MoraleFactors

    revolt_suppression_property: RevoltSuppressionProperty

    MAPPING = {
        "possible_upgrades": "possibleUpgrades",
        "queueable_upgrades": "queueableUpgrades",
        "possible_productions": "possibleProductions",
        "queueable_productions": "queueableProductions",
        "revolt_chance": "revoltChance",
        "uprising_chance": "uprisingChance",
        "target_morale": "targetMorale",
        "base_uprising_chance": "baseUprisingChance",
        "morale_factors": "moraleFactors",
        "revolt_suppression_property": "revoltSuppressionProperty",
    }
