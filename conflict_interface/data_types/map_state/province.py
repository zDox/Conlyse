from typing import Optional

from conflict_interface.data_types.common import RegionType
from .impact import Impact
from .province_production import ProvinceProduction
from .province_property import ProvinceProperty
from .terrain_type import TerrainType
from conflict_interface.data_types.resource_state import ResourceType


from dataclasses import dataclass
from enum import Enum


from conflict_interface.data_types.mod_state import ModableUpgrade
from .update_province_action import UpdateProvinceActionModes, UpdateProvinceAction
from ..custom_types import ArrayList, ProductionList
from ..custom_types import DefaultEnumMeta, HashSet
from ..game_object import GameObject
from ..point import Point


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
    properties: ProvinceProperty = None  # If player owns the provinc

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

    def build_upgrade(self, upgrade: ModableUpgrade):
        self.game.get_api().request_province_action(self.province_id, UpdateProvinceAction(
            province_ids=[self.province_id],
            mode=UpdateProvinceActionModes.UPGRADE,
            slot=0,
            upgrade=upgrade
        ).to_dict())

    def cancel_construction(self):
        self.game.get_api().request_province_action(self.province_id, UpdateProvinceAction(
            province_ids=[self.province_id],
            mode=UpdateProvinceActionModes.CANCEL_BUILDING,
            slot=0
        ).to_dict())

    def cancel_mobilization(self, province_id):
        self.game.get_api().request_province_action(province_id, UpdateProvinceAction(
            province_ids=[province_id],
            mode=UpdateProvinceActionModes.CANCEL_PRODUCING,
            slot=0,
        ).to_dict())


    def mobilize_unit(self, unit_type_id):
        if not self.properties:
            return
        targets = [special_unit for special_unit in self.properties.possible_productions
                    if special_unit.unit.unit_type_id == unit_type_id]
        if len(targets) == 0:
            return
        target = targets[0]
        self.game.get_api().request_province_action(self.province_id, UpdateProvinceAction(
            province_ids=[self.province_id],
            mode=UpdateProvinceActionModes.DEPLOYMENT_TARGET,
            slot=0,
            upgrade=target,
        ).to_dict())

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