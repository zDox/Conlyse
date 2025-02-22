from pprint import pprint
from typing import Optional

from conflict_interface.data_types.province import RegionType
from conflict_interface.data_types.resources.resource_types import ResourceType
from conflict_interface.utils import GameObject, ArrayList, LinkedList, ConMapping, Point, HashSet, Vector, \
    DefaultEnumMeta

from dataclasses import dataclass
from enum import Enum


from conflict_interface.data_types.upgrades.upgrade import ModableUpgrade
from conflict_interface.data_types.warfare import SpecialUnit, TerrainType


def position_to_tuple(value):
    if value:
        return (value["x"], value["y"])


def parse_resource_production_type(value):
    if value:
        return ResourceProductionType(value-1)
    else:
        return ResourceProductionType.NONE


class ProvinceStateID(Enum):
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



def parse_upgrades(value: list):
    if value is None:
        return
    return [ModableUpgrade.from_dict(upgrade) for upgrade in value[1]]


def parse_productions(value: list):
    if value is None:
        return

    return [SpecialUnit.from_dict(production) for production in value[1]]


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

@dataclass
class SeaProvince(GameObject):
    C = "ultshared.UltSeaProvince"
    province_id: int
    name: str
    center_coordinate: Point
    terrain_type: TerrainType

    def __hash__(self):
        return hash(self.province_id)

    MAPPING = {
        "province_id": "id",
        "name": "n",
        "center_coordinate": "c",
        "terrain_type": "tt",
    }

    def set_static_province(self, obj):
        pass


@dataclass
class Province(GameObject):
    C = "p"
    province_id: int

    # Data from GameServer
    province_state_id: ProvinceStateID
    name: str
    adjacent_to_water: bool
    resource_production: Optional[int]
    resource_production_type: ResourceType
    money_production: int
    victory_points: int
    owner_id: int
    upgrades: HashSet[ModableUpgrade]
    morale: int = 70
    legal_owner: int = -1

    # Data from Static supplier
    terrain_type: TerrainType = None
    center_coordinate: Point = None
    region: RegionType = RegionType.NONE
    properties: ProvinceProperty = None  # If player owns the province

    MAPPING = {
        "province_id": "id",
        "name": "n",
        "adjacent_to_water": "c",
        "owner_id": "o",
        "morale": "m",
        "province_state_id": "pst",
        "resource_production": "rp",
        "resource_production_type": ConMapping("r", ResourceProductionType),
        "money_production": "tp",
        "legal_owner": "lo",
        "victory_points": "plv",
        "upgrades": "us",
    }

    updateable_keys = ["province_state_id", "adjacent_to_water",
                       "resource_production", "money_production",
                       "victory_points", "owner_id", "legal_owner",
                       "moral", "buildings"]

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

class ProvinceUpdateActionModes(Enum):
    PROVINCE = 0
    UPGRADE = 1
    SPECIAL_UNIT = 2
    CANCEL_PRODUCING = 3
    CANCEL_BUILDING = 4
    DEPLOYMENT_TARGET = 5
    DEMOLISH_UPGRADE = 6

class UpdateProvinceAction(GameObject):
    province_ids: Vector[int]
    mode: ProvinceUpdateActionModes
    upgrade: ModableUpgrade
    slot: int = 0

    C = "ultshared.action.UltUpdateProvinceAction"
    MAPPING = {
        "province_ids": "provinceIDs",
        "mode": "mode",
        "slot": "slot",
        "upgrade": "upgrade",
    }

    def __init__(self, province_ids, mode, slot, upgrade=None, game=None):
        super().__init__(game)
        self.province_ids = province_ids
        self.mode = mode
        self.slot = slot
        self.upgrade = upgrade