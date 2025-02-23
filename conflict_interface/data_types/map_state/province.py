from typing import Optional

from conflict_interface.data_types.common import RegionType
from .province_property import ProvinceProperty
from .terrain_type import TerrainType
from conflict_interface.data_types.resource_state import ResourceType
from conflict_interface.utils import GameObject, ArrayList, LinkedList, ConMapping, Point, HashSet, Vector, \
    DefaultEnumMeta

from dataclasses import dataclass
from enum import Enum


from conflict_interface.data_types.mod_state import ModableUpgrade, SpecialUnit


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