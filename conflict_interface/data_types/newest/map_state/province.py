from dataclasses import dataclass
from functools import wraps
from typing import Optional

from ..custom_types import ArrayList
from ..custom_types import HashSet
from ..custom_types import ProductionList
from ..custom_types import Vector
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable
from ..map_state.impact import Impact
from ..map_state.map_state_enums import TerrainType
from ..map_state.province_action_result import UpdateProvinceActionResult
from ..map_state.map_state_enums import ProvinceStateID
from ..map_state.map_state_enums import ResourceProductionType
from ..map_state.province_production import ProvinceProduction
from ..map_state.province_property import ProvinceProperty
from ..map_state.static_province import StaticProvince
from ..map_state.update_province_action import UpdateProvinceAction
from ..map_state.update_province_action import UpdateProvinceActionModes
from ..mod_state.modable_unit import SpecialUnit
from ..mod_state.moddable_upgrade import ModableUpgrade
from ..player_state.player_profile import PlayerProfile
from ..point import Point
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode
from conflict_interface.utils.exceptions import ActionException

logger = get_logger()


def requires_ownership(func):
    """Decorator to ensure certain methods are executed only if ownership is verified."""

    @wraps(func)
    def wrapper(self: "Province", *args, **kwargs):
        if self.is_owner():
            return func(self, *args, **kwargs)
        else:
            raise ActionException(f"Current player does not own province {self.id}. Action denied.")

    return wrapper

from ..version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class Province(GameObject):
    """
    Represents a Province which is a part of a game structure.

    It includes detailed state and configuration data for the province derived from both the game server
    and static data sources. It also provides mechanisms to update or modify
    its state dynamically during gameplay.

    Attributes:
        id: Identifier for the province.
        province_state_id: State ID representing the current status of the province. E.x. if the province is occupied
        name: Name of the province.
        resource_production: Amount of resources produced by the province, if applicable.
        resource_production_type: Type of resource produced by the province.
        money_production: Amount of money produced by the province.
        victory_points: The number of victory points attributed to the province.
        owner_id: ID of the player who currently owns the province.
        morale: Morale of the province, with a default value of 70.
        legal_owner: ID of the legal owner of the province or -1 if no legal owner.
        constructions (ProductionList[Optional[ProvinceProduction]]): The List has 4 entries. In slot 0 is the upgrade that is
            visible to the owner of the province. Slot 1,2 are unknown and are so it seems always None. Slot 3 is the slot
            where the Population is built to the next level. Population is a building not visible to the player.
        production (Optional[ProvinceProduction]): Unit that is currently being mobilized in this province.
            This is the upgrade that is visible to the owner of the province
        productions (ProductionList[Optional[ProvinceProduction]]): The list holds all currently units that are
            currently being produced in this province. So far we only encountered lists with a single entry.

    """
    C = "p"
    id: int

    # Data from GameServer
    province_state_id: ProvinceStateID

    center_coordinate: Point
    resource_production: Optional[int]
    resource_production_type: ResourceProductionType

    victory_points: int
    owner_id: int
    upgrades_set: HashSet[ModableUpgrade]

    stationary_army: Optional[int]
    base_production: int

    core_ids: list[int]

    last_battle: Optional[int]
    impacts: Optional[ArrayList[Impact]]

    production: Optional[ProvinceProduction]
    productions: Optional[ProductionList[Optional[ProvinceProduction]]]
    terrain_type: TerrainType

    constructions: Optional[ProductionList[Optional[ProvinceProduction]]]
    costal: bool = False
    money_production: int = 0
    morale: int = 70
    legal_owner: int = -1
    name: str = ""

    _properties: ProvinceProperty = None  # If player owns the province
    _upgrades: dict[int, ModableUpgrade] = None
    _static_data: StaticProvince = None


    MAPPING = {
        "id": "id",
        "name": "n",
        "center_coordinate": "c",
        "owner_id": "o",
        "morale": "m",
        "province_state_id": "pst",
        "resource_production": "rp",
        "resource_production_type": "r",
        "money_production": "tp",
        "legal_owner": "lo",
        "victory_points": "plv",
        "upgrades_set": "us",
        "stationary_army": "sa",
        "base_production": "bp",
        "core_ids": "ci",
        "last_battle": "lb",
        "impacts": "ims",
        "costal": "co",
        "constructions": "cos",
        "production": "pi",
        "productions": "prs",
        "terrain_type": "tt"
    }

    updateable_keys = ["province_state_id",
                       "resource_production",
                       "resource_production_type",
                       "base_production",
                       "money_production",
                       "victory_points",
                       "last_battle",
                       "production",
                       "productions",
                       "constructions",
                       "core_ids",
                       "owner_id",
                       "legal_owner",
                       "morale",
                       "upgrades_set"]

    def is_owner(self):
        return self.owner_id == self.game.player_id

    @property
    def owner(self) -> PlayerProfile:
        return self.game.get_player(self.owner_id)

    @property
    def properties(self) -> ProvinceProperty | None:
        if self._properties:
            return self._properties
        else:
            self._properties = self.game.game_state.states.map_state.properties.get(self.id)
            return self._properties

    @property
    def upgrades(self) -> dict[int, ModableUpgrade]:
        if not self._upgrades:
            self._upgrades = {
                upgrade.id: upgrade
                for upgrade in self.upgrades_set
            }
        return self._upgrades

    @property
    def static_data(self) -> StaticProvince:
        if not self._static_data:
            self._static_data = self.game.get_map().static_map_data.province_to_location[self.id]

        return self._static_data

    @requires_ownership
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

    @requires_ownership
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
    def get_upgrade_buildability(self, upgrade: ModableUpgrade) -> UpdateProvinceActionResult:
        """
        Determine if an upgrade can be built in the current province.

        Args:
            upgrade (ModableUpgrade): The upgrade to check.

        Returns:
            UpdateProvinceActionResult: UpdateProvinceActionResult.Ok if the upgrade can be built,
                otherwise the reason why it can't be built.
        """
        # TODO Check if player has necessary resources
        slot_0 = self.constructions[0] if self.constructions else None
        if slot_0 is not None:
            return UpdateProvinceActionResult.AlreadyConstructingUpgrade
        elif upgrade not in self.properties.possible_upgrades:
            return UpdateProvinceActionResult.UpgradeNotAvailable
        return UpdateProvinceActionResult.Ok

    @requires_ownership
    def is_upgrade_buildable(self, upgrade: ModableUpgrade) -> bool:
        return self.get_upgrade_buildability(upgrade) == UpdateProvinceActionResult.Ok

    @requires_ownership
    def build_upgrade(self, upgrade: ModableUpgrade) -> tuple[Optional[int], UpdateProvinceActionResult]:
        """
        Performs the action of building an upgrade in the current province if the upgrade
        is buildable. This operation checks the prerequisites for the upgrade and triggers
        the game action to update the province state with the specified upgrade.

        Parameters:
            upgrade (ModableUpgrade): The upgrade to be built in the province.

        Returns:
            tuple[Optional[int], UpdateProvinceActionResult]: A tuple where the first element
            is the identifier of the successful action if applicable (otherwise None), and
            the second element is the result status indicating success or the reason for
            inability to build the upgrade.
        """
        if self.is_upgrade_buildable(upgrade):
            return self.game.online.do_action(UpdateProvinceAction(
                province_ids=Vector([self.id]),
                mode=UpdateProvinceActionModes.UPGRADE,
                slot=0,
                upgrade=upgrade,
            )), UpdateProvinceActionResult.Ok
        else:
            return None, self.get_upgrade_buildability(upgrade)

    @requires_ownership
    def cancel_construction(self) -> tuple[Optional[int], UpdateProvinceActionResult]:
        """
            Cancel ongoing construction in the current province if any construction
            exists. If no construction is present, the function immediately returns
            a specific result indicating no ongoing production. If construction
            exists, it invokes the game's action system to handle the cancellation
            and returns the outcome.

            Parameters:
                self (Province): Represents the current province instance where the
                cancel construction action will be applied.

            Returns:
                tuple[Optional[int], UpdateProvinceActionResult]: A tuple where the
                first element is the unique action id or None, indicating the Action was
                a failure. The second element is the result enumerating the
                outcome of the cancellation attempt.
        """

        if self.constructions is None or self.constructions[0] is None:
            return None, UpdateProvinceActionResult.NoProduction

        return self.game.online.do_action(UpdateProvinceAction(
            province_ids=Vector([self.id]),
            mode=UpdateProvinceActionModes.CANCEL_BUILDING,
            slot=0
        )), UpdateProvinceActionResult.Ok


    def is_demolishable(self, upgrade_id: int) -> bool:
        """
        Determines if a specific upgrade can be demolished.
        Args:
            upgrade_id (int): The unique identifier for the upgrade.

        Returns:
            bool: True if the upgrade can be demolished, False otherwise.
        """
        upgrade = self.upgrades.get(upgrade_id)
        if upgrade:
            return True
        return False

    @requires_ownership
    def demolish_upgrade(self, upgrade_id: int) -> tuple[Optional[int], UpdateProvinceActionResult]:
        """
        Demolishes an upgrade, if eligible, within the associated province. This method checks whether the specified
        upgrade can be demolished and performs the required game action.

        :param: upgrade_id (int): The unique identifier of the upgrade to be demolished.

        :return: tuple[Optional[int], UpdateProvinceActionResult]
            A tuple containing the optional unique action id and the result of the operation.
        """

        if not isinstance(upgrade_id, int):
            raise ValueError("upgrade_id must be an integer")
        if self.is_demolishable(upgrade_id):
            upgrade = self.upgrades.get(upgrade_id)
            return self.game.online.do_action(UpdateProvinceAction(province_ids=Vector([self.id]),
                                                            mode=UpdateProvinceActionModes.DEMOLISH_UPGRADE,
                                                            slot=0,
                                                            upgrade=upgrade)), UpdateProvinceActionResult.Ok
        return None, UpdateProvinceActionResult.NotDemolishable


    @requires_ownership
    def get_unit_mobilizability(self, unit: SpecialUnit) -> UpdateProvinceActionResult:
        """
        Determine if an upgrade can be built in the current province.

        Args:
            unit (SpecialUnit): The upgrade to check.

        Returns:
            bool: True if the upgrade can be built, False otherwise.
        """
        # TODO Check if player has necessary resources
        if self.production is not None:
            return UpdateProvinceActionResult.AlreadyMobilizingUnit
        elif unit not in self.properties.possible_productions:
            return UpdateProvinceActionResult.UnitNotAvailable
        return UpdateProvinceActionResult.Ok

    @requires_ownership
    def is_unit_mobilizable(self, unit: SpecialUnit) -> bool:
        """
        Returns True if the unit is available for mobilization in the province, False otherwise.
        """
        return self.get_unit_mobilizability(unit) == UpdateProvinceActionResult.Ok

    @requires_ownership
    def get_possible_production_by_unit_type_id(self, unit_type_id: int) -> SpecialUnit | None:
        """
        Returns the possible production corresponding to the given unit type id.

        :param: unit_type_id (int): The unit type id of which we want to find the production for.

        :returns: SpecialUnit or None
        """
        for production in self.get_possible_productions():
            if production.unit.unit_type_id == unit_type_id:
                return production

    @requires_ownership
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

    @requires_ownership
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

        if self.is_unit_mobilizable(unit):
            return self.game.online.do_action(UpdateProvinceAction(
                province_ids=Vector([self.id]),
                mode=UpdateProvinceActionModes.SPECIAL_UNIT,
                slot=0,
                upgrade=unit,
            )), UpdateProvinceActionResult.Ok
        else:
            return None, self.get_unit_mobilizability(unit)

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
            return None, UpdateProvinceActionResult.NoProduction

        return self.game.online.do_action(UpdateProvinceAction(
            province_ids=Vector([self.id]),
            mode=UpdateProvinceActionModes.CANCEL_PRODUCING,
            slot=0,
        )), UpdateProvinceActionResult.Ok

    def has_construction(self, slot: int) -> bool:
        return self.constructions[slot] is not None

    @property
    def population(self) -> int | None:
        if self.constructions is None:
            return None
        if self.constructions[3] is None:
            return None
        upgrade = self.constructions[3].upgrade
        if not isinstance(upgrade, ModableUpgrade):
            return None
        return upgrade.get_upgrade_type().tier - 1

    def has_upgrades(self, required_upgrades: list[int]) -> bool:
        for required_upgrade in required_upgrades:
            has_upgrade = False
            for upgrade in self.upgrades.values():
                if upgrade.id == required_upgrade:
                    has_upgrade = True
                    break
            if not has_upgrade:
                return False
        return True

    def update(self, other: "Province", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        for updateable_key in Province.updateable_keys:
            if rp and getattr(self, updateable_key) != getattr(other, updateable_key):
                rp.replace(path + [updateable_key], getattr(self, updateable_key), getattr(other, updateable_key))
            setattr(self, updateable_key, getattr(other, updateable_key))

    def __hash__(self):
        return hash(self.id)