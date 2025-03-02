from functools import wraps
from typing import Optional


from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.mod_state.modable_unit import SpecialUnit
from conflict_interface.data_types.custom_types import ArrayList, Vector
from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.custom_types import HashSet
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade
from conflict_interface.data_types.custom_types import ProductionList
from conflict_interface.data_types.common.enums.region_type import RegionType
from conflict_interface.data_types.resource_state.resource_types import ResourceType
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

class ProvinceStateID(Enum, metaclass=DefaultEnumMeta):
    """
    Enumeration for representing different types of administrative areas.

    Attributes:
        OCCUPIED_PROVINCE: Represents a province under occupation.
        MAINLAND_PROVINCE: Represents a province within the mainland.
        OCCUPIED_CITY: Represents a city under occupation.
        ANNEXED_CITY: Represents a city annexed to a different territory.
        MAINLAND_CITY: Represents a city within the mainland.
    """
    NONE = 0
    OCCUPIED_PROVINCE = 51
    MAINLAND_PROVINCE = 52
    OCCUPIED_CITY = 53
    ANNEXED_CITY = 54
    MAINLAND_CITY = 55


class ResourceProductionType(Enum, metaclass=DefaultEnumMeta):
    NONE = ResourceType.NONE.value + 1
    SUPPLY = ResourceType.SUPPLY.value + 1
    COMPONENT = ResourceType.COMPONENT.value + 1
    MANPOWER = ResourceType.MANPOWER.value + 1
    RARE_MATERIAL = ResourceType.RARE_MATERIAL.value + 1
    FUEL = ResourceType.FUEL.value + 1
    ELECTRONIC = ResourceType.ELECTRONIC.value + 1
    CONVENTIONAL_WARHEAD = ResourceType.CONVENTIONAL_WARHEAD.value + 1
    CHEMICAL_WARHEAD = ResourceType.CHEMICAL_WARHEAD.value + 1
    NUCLEAR_WARHEAD = ResourceType.NUCLEAR_WARHEAD.value + 1
    DEPLOYABLE_GEAR = ResourceType.DEPLOYABLE_GEAR.value + 1
    MONEY = ResourceType.MONEY.value + 1
    CITY_CLAIM = ResourceType.CITY_CLAIM.value + 1
    PHARMACEUTICAL = ResourceType.PHARMACEUTICAL.value + 1

    def to_py(self, type):
        if type != ResourceType:
            raise ValueError(f"type ({type}) must be ResourceType")
        if self.value == 0:
            return ResourceType(0)
        return ResourceType(self.value-1)


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
        "production": "bi", # TODO why the fuck bi??
        "productions": "cos" # TODO what the heck cos??

    }

    updateable_keys = ["province_state_id", "adjacent_to_water",
                       "resource_production", "money_production",
                       "victory_points", "owner_id", "legal_owner",
                       "moral", "buildings"]

    def is_owner(self):
        return self.owner_id == self.game.player_id

    @property
    def properties(self) -> ProvinceProperty | None:
        if self._properties:
            return self._properties
        else:
            self._properties = self.game.game_state.states.map_state.properties.get(self.province_id)
            return self._properties

    def get_possible_upgrades(self, **filters) -> list[ModableUpgrade]:
        if not self.is_owner():
            return []
        else:
            return [mu for mu in self.properties.possible_upgrades
                    if all(getattr(mu, key) == value for key, value in filters.items())]

    def get_possible_productions(self, **filters) -> list[ModableUpgrade]:
        if not self.is_owner():
            return []
        else:
            return [mu for mu in self.properties.possible_productions
                    if all(getattr(mu, key) == value for key, value in filters.items())]

    @requires_ownership
    def build_upgrade(self, upgrade: ModableUpgrade):
        self.check_ownership()
        if upgrade in self.properties.possible_upgrades:
            self.game.do_action(UpdateProvinceAction(
                province_ids=Vector([self.province_id]),
                mode=UpdateProvinceActionModes.UPGRADE,
                slot=0,
                upgrade=upgrade,
            ))
        else:
            raise ActionException(f"Upgrade {upgrade.id} is not available for province {self.province_id}.")

    @requires_ownership
    def cancel_construction(self):
        self.check_ownership()
        if self.production is None:
            logger.warning(f"Trying to cancel construction but Province {self.province_id} has no production.")
            return

        self.game.do_action(UpdateProvinceAction(
            province_ids=Vector([self.province_id]),
            mode=UpdateProvinceActionModes.CANCEL_BUILDING,
            slot=0
        ))

    @requires_ownership
    def cancel_mobilization(self, province_id):
        self.check_ownership()
        # TODO Check if province is mobilizing something
        self.game.do_action(UpdateProvinceAction(
            province_ids=Vector([province_id]),
            mode=UpdateProvinceActionModes.CANCEL_PRODUCING,
            slot=0,
        ))

    @requires_ownership
    def mobilize_unit(self, unit: SpecialUnit):
        self.check_ownership()
        if unit in self.properties.possible_productions:
            self.game.do_action(UpdateProvinceAction(
                province_ids=Vector([self.province_id]),
                mode=UpdateProvinceActionModes.DEPLOYMENT_TARGET,
                slot=0,
                upgrade=unit,
            ))
        else:
            raise ActionException(f"Unit {unit.unit.unit_type_id} is not available for province {self.province_id}.")


    def set_static_province(self, obj):
        for static_field in StaticProvince.__annotations__.keys():
            setattr(self, static_field, getattr(obj, static_field))

    def update(self, new_province):
        for updateable_key in Province.updateable_keys:
            setattr(self, updateable_key,
                    getattr(new_province, updateable_key))

    def __hash__(self):
        return hash(self.province_id)

@dataclass
class StaticProvince(GameObject):
    """
    Represents a static province within a game context.

    Attributes:
        id: Unique identifier for the province within the game system.
        terrain_type: Type of terrain associated with the province.
        center_coordinate: Geographic center of the province as a point.
        region: List of regions related to the province.
    """
    id: int
    terrain_type: TerrainType
    center_coordinate: Point
    region: list[RegionType] = None

    MAPPING = {
        "id": "id",
        "terrain_type": "tt",
        "center_coordinate": "c",
        "region": "rg",
    }