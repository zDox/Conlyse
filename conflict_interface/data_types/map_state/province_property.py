from dataclasses import dataclass
from typing import Union

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.map_state.morale_factors import MoraleFactors
from conflict_interface.data_types.map_state.map_state_enums import RevoltSuppressionProperty
from conflict_interface.data_types.mod_state.modable_unit import SpecialUnit
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade
from conflict_interface.data_types.custom_types import LinkedList, ArrayList, EmptyList


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
    possible_upgrades: Union[EmptyList[ModableUpgrade], LinkedList[ModableUpgrade], ArrayList[ModableUpgrade]]
    queueable_upgrades: Union[EmptyList[ModableUpgrade], LinkedList[ModableUpgrade], ArrayList[ModableUpgrade]]

    possible_productions: Union[EmptyList[SpecialUnit], LinkedList[SpecialUnit], ArrayList[SpecialUnit]]
    queueable_productions: Union[EmptyList[SpecialUnit], LinkedList[SpecialUnit], ArrayList[SpecialUnit]]

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


    def update_possible_upgrades(self, province_id: int):
        province = self.game.get_province(province_id)
        if province is None:
            return
        self.possible_upgrades = ArrayList([])
        if province.has_construction(0):
            return None

        # Upgrades that replace any of the current ones
        for upgrade in province.upgrades.values():
            upgrade_type = self.game.get_upgrade_type(upgrade.id)
            if upgrade_type is None:
                continue
            replacing_upgrade_type = self.game.get_upgrade_type(upgrade_type.get_replacing_upgrade())
            if replacing_upgrade_type is None:
                continue
            if not province.has_upgrades(list(replacing_upgrade_type.required_upgrades.keys())):
                continue
            if upgrade.condition == upgrade_type.max_condition:
                self.possible_upgrades.append(ModableUpgrade(
                    id=replacing_upgrade_type.id,
                    relative_position=None,
                    condition=0,
                ))
            else:
                self.possible_upgrades.append(ModableUpgrade(
                    id=upgrade.id,
                    relative_position=None,
                    condition=0,
                ))
        # Upgrades that are base upgrades
        for upgrade in self.game.get_upgrade_types(tier=1).values():
            if any([upgrade.sorting_order == self.game.get_upgrade_type(possible_upgrade.id).sorting_order for possible_upgrade in self.possible_upgrades]):
                # Upgrade from same group is already possible. Lower level one shouldn't be possible to build.
                continue
            if province.province_state_id not in upgrade.possible_province_states:
                continue
            self.possible_upgrades.append(ModableUpgrade(
                id=upgrade.id,
                relative_position=None,
                condition=0,
            ))