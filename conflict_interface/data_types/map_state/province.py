from functools import wraps
from typing import Optional

from dataclasses import dataclass

from conflict_interface.data_types.map_state.province_enums import ProvinceStateID
from conflict_interface.data_types.map_state.province_enums import ResourceProductionType
from conflict_interface.data_types.map_state.static_province import StaticProvince

from conflict_interface.data_types.mod_state.modable_unit import SpecialUnit
from conflict_interface.data_types.custom_types import ArrayList, Vector
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import HashSet
from conflict_interface.data_types.custom_types import ProductionList
from conflict_interface.data_types.common.enums.region_type import RegionType
from conflict_interface.data_types.map_state.terrain_type import TerrainType
from conflict_interface.data_types.map_state.update_province_action import UpdateProvinceAction
from conflict_interface.data_types.map_state.update_province_action import UpdateProvinceActionModes
from conflict_interface.data_types.map_state.impact import Impact
from conflict_interface.data_types.map_state.province_production import ProvinceProduction
from conflict_interface.data_types.map_state.province_property import ProvinceProperty
from conflict_interface.data_types.point import Point

from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade
from conflict_interface.logger_config import get_logger
from conflict_interface.utils.exceptions import ActionException

logger = get_logger()


def requires_ownership(func):
    """Decorator to ensure certain methods are executed only if ownership is verified."""

    @wraps(func)
    def wrapper(self: "Province", *args, **kwargs):
        if self.is_owner():
            return func(self, *args, **kwargs)
        else:
            raise ActionException(f"Current player does not own province {self.province_id}. Action denied.")

    return wrapper


@dataclass
class Province(GameObject):
    """
    Represents a Province which is a part of a game structure.

    It includes detailed state and configuration data for the province derived from both the game server
    and static data sources. It also provides mechanisms to update or modify
    its state dynamically during gameplay.

    Attributes:
        province_id: Identifier for the province.
        province_state_id: State ID representing the current status of the province. E.x. if the province is occupied
        name: Name of the province.
        adjacent_to_water: Indicates whether the province is situated adjacent to a water body.
        resource_production: Amount of resources produced by the province, if applicable.
        resource_production_type: Type of resource produced by the province.
        money_production: Amount of money produced by the province.
        victory_points: The number of victory points attributed to the province.
        owner_id: ID of the player who currently owns the province.
        upgrades: Upgrades applied to the province.
        morale: Morale of the province, with a default value of 70.
        legal_owner: ID of the legal owner of the province or -1 if no legal owner.
        terrain_type: Type of terrain in the province. Defaults to None until set.
        center_coordinate: Coordinates representing the central location of the province. Defaults to None until set.
        region: Region to which the province belongs. Defaults to RegionType.NONE.
        properties: Properties associated with the province, need to be owned by the current player. Defaults to None.
        construction (Optional[ProvinceProduction]): Upgrade that is currently being constructed in this province.
            This is the upgrade that is visible to the owner of the province
        constructions (ProductionList[Optional[ProvinceProduction]]): The List has 4 entries. In slot 0 is the upgrade that is
            visible to the owner of the province. Slot 1,2 are unknown and are so it seems always None. Slot 3 is the slot
            where the Population is built to the next level. Population is a building not visible to the player.
        construction_slots (ProductionList[Optional[ProvinceProduction]]): Never encountered dont know what preceisly is
            in there.
        production (Optional[ProvinceProduction]): Unit that is currently being mobilized in this province.
            This is the upgrade that is visible to the owner of the province
        productions (ProductionList[Optional[ProvinceProduction]]): The list holds all currently units that are
            currently being produced in this province. So far we only encountered lists with a single entry.
        production_slots (ProductionList[Optional[ProvinceProduction]]): Never encountered dont know what preceisly is
            in there.


    """
    C = "p"
    province_id: int

    # Data from GameServer
    province_state_id: ProvinceStateID

    adjacent_to_water: bool
    resource_production: Optional[int]
    resource_production_type: ResourceProductionType

    victory_points: int
    owner_id: int
    upgrades: HashSet[ModableUpgrade]

    stationary_army: Optional[int]
    base_production: int

    core_ids: list[int]

    last_battle: Optional[int]
    impacts: Optional[ArrayList[Impact]]

    production: Optional[ProvinceProduction]
    productions: Optional[ProductionList[ProvinceProduction]]
    production_slots: Optional[ProductionList[ProvinceProduction]]

    construction: Optional[ProvinceProduction]
    constructions: Optional[ProductionList[ProvinceProduction]]
    construction_slots: Optional[ProductionList[ProvinceProduction]]
    costal: bool = False
    money_production: int = 0
    morale: int = 70
    legal_owner: int = -1

    # Data from Static supplier
    name: str = ""
    terrain_type: TerrainType = None
    center_coordinate: Point = None
    region: RegionType = RegionType.NONE
    _properties: ProvinceProperty = None  # If player owns the province

    MAPPING = {
        "province_id": "id",
        "name": "n",
        "adjacent_to_water": "c",
        "owner_id": "o",
        "morale": "m",
        "province_state_id": "pst",
        "resource_production": "rp",
        "resource_production_type": "r",
        "money_production": "tp",
        "legal_owner": "lo",
        "victory_points": "plv",
        "upgrades": "us",
        "stationary_army": "sa",
        "base_production": "bp",
        "core_ids": "ci",
        "last_battle": "lb",
        "impacts": "ims",
        "costal": "co",
        "construction": "bi",  # TODO why the fuck bi??
        "constructions": "cos",  # TODO what the heck cos??
        "production": "pi",
        "productions": "prs",
        "construction_slots": "cs",
        "production_slots": "ps",

    }

    updateable_keys = ["province_state_id", "adjacent_to_water",
                       "resource_production", "money_production",
                       "victory_points", "owner_id", "legal_owner",
                       "moral", "buildings"]

    def is_owner(self):
        return self.owner_id == self.game.player_id

    def debug_str(self):
        return f"{self.name}({self.province_id})"

    @property
    def properties(self) -> ProvinceProperty | None:
        if self._properties:
            return self._properties
        else:
            self._properties = self.game.game_state.states.map_state.properties.get(self.province_id)
            return self._properties

    def get_possible_upgrade(self, **filters) -> ModableUpgrade | None:
        """
        Return the first upgrade that matches the given filters.
        """
        if not self.is_owner():
            return None
        else:
            upgrades = self.get_possible_upgrades(**filters)
            if upgrades:
                return upgrades[0]
            else:
                return None

    def get_possible_upgrades(self, **filters) -> list[ModableUpgrade]:
        """
        Returns the list of possible upgrades that match the specified filters for the
        current object if the user is an owner. If the user is not an owner, an empty
        list is returned.

        Arguments:
            **filters: Arbitrary keyword arguments representing filtering criteria
                       where the key is the attribute of a possible upgrade and the
                       value is the expected value for the filtering.

        Returns:
            list[ModableUpgrade]: A list of upgrades that match the filter criteria, or
                                  an empty list if the user is not the owner.
        """
        if not self.is_owner():
            return []
        else:
            return [mu for mu in self.properties.possible_upgrades
                    if all(getattr(mu, key) == value for key, value in filters.items())]

    @requires_ownership
    def is_upgrade_buildable(self, upgrade: ModableUpgrade) -> bool:
        """
        Determine if an upgrade can be built in the current province.

        Args:
            upgrade (ModableUpgrade): The upgrade to check.

        Returns:
            bool: True if the upgrade can be built, False otherwise.
        """
        # TODO Check if player has necessary resources
        slot_0 = self.construction
        if slot_0 is not None:
            return False
        elif upgrade is None:
            return False
        elif upgrade not in self.properties.possible_upgrades:
            return False
        return True

    @requires_ownership
    def build_upgrade(self, upgrade: ModableUpgrade):
        """
        Applies an upgrade to a province if the upgrade is available in the
        current province's list of possible upgrades.

        This method checks if the given upgrade is among the possible upgrades
        for the current province and applies it using the game's update action.
        If the upgrade is not available, an exception is raised.

        @requires_ownership Decorator to ensure that the caller has ownership
        rights over the province before executing the method.

        Args:
            upgrade (ModableUpgrade): The upgrade intended to be built in the province.

        Raises:
            ActionException: When the specified upgrade is not available for
            the province.
        """
        if self.construction is not None:
            raise ActionException(f"Province {self.debug_str()} is already building {self.construction.upgrade.debug_str()}.")

        if upgrade is None:
            raise ActionException(f"Upgrade None cannot be built in Province {self.debug_str()}.")
        elif upgrade in self.properties.possible_upgrades:
            self.game.do_action(UpdateProvinceAction(
                province_ids=Vector([self.province_id]),
                mode=UpdateProvinceActionModes.UPGRADE,
                slot=0,
                upgrade=upgrade,
            ))
        else:
            raise ActionException(f"Upgrade {upgrade.id} is not available for province {self.debug_str()}.")

    @requires_ownership
    def cancel_construction(self):
        """
        Cancels the ongoing construction of a building in the given province. If no production is currently
        associated with the province, the method will log a warning and take no further action.

        @requires_ownership Decorator to ensure that the caller has ownership
        rights over the province before executing the method.
        """

        if self.construction is None:
            logger.warning(f"Trying to cancel construction but Province {self.debug_str()} has no production.")
            return


        self.game.do_action(UpdateProvinceAction(
            province_ids=Vector([self.province_id]),
            mode=UpdateProvinceActionModes.CANCEL_BUILDING,
            slot=0
        ))

    @requires_ownership
    def is_unit_mobilizable(self, unit: SpecialUnit) -> bool:
        """
        Determine if an upgrade can be built in the current province.

        Args:
            unit (SpecialUnit): The upgrade to check.

        Returns:
            bool: True if the upgrade can be built, False otherwise.
        """
        # TODO Check if player has necessary resources
        if self.production is not None:
            return False
        elif unit is None:
            return False
        elif unit not in self.properties.possible_productions:
            return False
        return True

    def get_possible_production_by_unit_type_id(self, unit_type_id: int) -> SpecialUnit | None:
        """
        Returns the possible production corresponding to the given unit type id.

        :param: unit_type_id (int): The unit type id of which we want to find the production for.

        :returns: SpecialUnit or None
        """
        for production in self.get_possible_productions():
            if production.unit.unit_type_id == unit_type_id:
                return production


    def get_possible_production(self, **filters) -> SpecialUnit | None:
        """
        Return the first unit that matches the given filters.
        """
        if not self.is_owner():
            return None
        else:
            productions = self.get_possible_productions(**filters)
            if productions:
                return productions[0]
            else:
                return None

    def get_possible_productions(self, **filters) -> list[SpecialUnit]:
        """
        Gets a filtered list of possible productions based on the provided filters.

        If the instance is not owned, an empty list is returned.

        Parameters:
            filters: Arbitrary keyword arguments used as filters. The filters
                     must match the attributes of `SpecialUnit`. Each key-value
                     pair in the filters represents the attribute name and the desired
                     value for filtering.

        Returns:
            list[SpecialUnit]: A list of `SpecialUnit` objects that match
            the given filters. Returns an empty list if the instance is not
            owned or if no items match the filters.
        """
        if not self.is_owner():
            return []
        else:
            return [mu for mu in self.properties.possible_productions
                    if all(getattr(mu, key) == value for key, value in filters.items())]

    @requires_ownership
    def mobilize_unit_by_id(self, unit_type_id: int):
        """
        Mobilizes a unit which has the unit_type_id in this province.

        This method checks if the provided unit is available for production in the province.


        @requires_ownership Decorator to ensure that the caller has ownership
        rights over the province before executing the method.

        Parameters:
            unit_type_id (int): The identifier for unit type to mobilize in this province.

        Raises:
            ActionException:
        """
        unit = self.get_possible_production_by_unit_type_id(unit_type_id)
        if self.production is not None:
            raise ActionException(f"Province {self.debug_str()} is already mobilizing {self.production.upgrade.debug_str()}).")
        if unit is None:
            raise ActionException(f"Unit None cannot be mobilized in Province {self.debug_str()}).")
        elif unit in self.properties.possible_productions:
            self.game.do_action(UpdateProvinceAction(
                province_ids=Vector([self.province_id]),
                mode=UpdateProvinceActionModes.SPECIAL_UNIT,
                slot=0,
                upgrade=unit,
            ))
        else:
            raise ActionException(f"Unit {unit.debug_str()} is not available for province {self.debug_str()}.")

    @requires_ownership
    def cancel_mobilization(self):
        """
        Cancels the mobilization process for a specific province. This function ensures
        that any ongoing production or mobilization in the specified province is
        terminated.

        @requires_ownership Decorator to ensure that the caller has ownership
        rights over the province before executing the method.
        """
        if self.production is None:
            logger.warning(f"Trying to cancel mobilization but Province {self.debug_str()} has no production.")
            return

        self.game.do_action(UpdateProvinceAction(
            province_ids=Vector([self.province_id]),
            mode=UpdateProvinceActionModes.CANCEL_PRODUCING,
            slot=0,
        ))

    def set_static_province(self, obj):
        for static_field in StaticProvince.__annotations__.keys():
            setattr(self, static_field, getattr(obj, static_field))

    def update(self, new_province):
        for updateable_key in Province.updateable_keys:
            setattr(self, updateable_key,
                    getattr(new_province, updateable_key))

    def __hash__(self):
        return hash(self.province_id)