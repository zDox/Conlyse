from data_types.utils import JsonMappedClass, MappedValue
from data_types.warfare_unit import SpecialUnit

from dataclasses import dataclass
from enum import Enum


def position_to_tuple(value):
    if value:
        return (value["x"], value["y"])


def parse_resource_production_type(value):
    if value:
        return ResourceProductionType(value-1)
    else:
        return ResourceProductionType.NONE


class TerrainType(Enum):
    PLAINS = 10
    HILLS = 11
    MOUNTIN = 12
    FOREST = 13
    URBAN = 14
    JUNGLE = 15
    TUNDRA = 16
    DESERT = 17
    SEA = 18
    HIGHSEA = 19
    COASTAL = 20
    SUBURBAN = 21


class ProvinceStateID(Enum):
    NONE = -1
    OCCUPIED_PROVINCE = 51
    MAINLAND_PROVINCE = 52
    OCCUPIED_CITY = 53
    ANNEXED_CITY = 54
    MAINLAND_CITY = 55


class ResourceProductionType(Enum):
    NONE = 0
    SUPPLIES = 1
    COMPONENTS = 2
    MANPOWER = 3
    RARE_MATERIALS = 4
    FUEL = 5
    ELECTRONICS = 6
    CONVENTIONAL_WARHEAD = 8
    CHEMICAL_WARHEAD = 8
    NUCLEAR_WARHEAD = 9
    DEPLOYABLE_GEAR = 10
    MONEY = 20


class Region(Enum):
    NONE = -1
    EUROPA = 0
    ASIA = 1
    AFRICA = 2
    NORTH_AMERICA = 3
    SOUTH_AMERICA = 4
    OCEANIA = 5


@dataclass
class Building(JsonMappedClass):
    health: int
    harbour_coordinate: tuple[int, int]
    upgrade_id: int
    constructing: bool

    mapping = {
            "health": "c",
            "harbour_coordinate": MappedValue("rp", position_to_tuple),
            "upgrade_id": "id",
            "constructing": "cn",
    }


def rg_to_region(value: list):
    if value is not None and len(value) != 0:
        return Region(value[0])
    else:
        Region.NONE


def parse_buildings(value: list):
    if value is None:
        return

    return [Building.from_dict(building) for building in value[1]]


@dataclass
class Province(JsonMappedClass):
    id: int

    # Data from GameServer
    province_state_id: ProvinceStateID
    name: str
    adjacent_to_water: bool
    resource_production: int
    resource_production_type: ResourceProductionType
    money_production: int
    victory_points: int
    owner_id: int
    legal_owner: int
    morale: int
    buildings: list[Building]

    # Data from Static supplier
    terrain_type: TerrainType = None
    center_coordinate: tuple[int, int] = None
    region: Region = Region.NONE

    mapping = {
        "id": "id",
        "name": "n",
        "adjacent_to_water": "c",
        "owner_id": "o",
        "morale": "m",
        "province_state_id": "pst",
        "resource_production": "rp",
        "resource_production_type": MappedValue(
            "r", parse_resource_production_type),
        "money_production": "tp",
        "legal_owner": "lo",
        "victory_points": "plv",
        "buildings": MappedValue("us", parse_buildings),
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


@dataclass
class StaticProvince(JsonMappedClass):
    id: int
    terrain_type: TerrainType
    center_coordinate: tuple[int, int]
    region: Region

    mapping = {
        "id": "id",
        "terrain_type": "tt",
        "center_coordinate": MappedValue("c", position_to_tuple),
        "region": MappedValue("rg", rg_to_region),
    }


def parse_productions(value: list):
    if value is None:
        return

    return [SpecialUnit.from_dict(production) for production in value[1]]


@dataclass
class ProvinceProperty(JsonMappedClass):
    id: int  # Province ID
    possible_upgrades: list[Building]
    queueable_upgrades: list[Building]

    possible_productions: list[SpecialUnit]
    queueable_productions: list[SpecialUnit]

    revolt_chance: int
    uprising_chance: int
    target_morale: int

    mapping = {
        "id": "id",
        "possible_upgrades": MappedValue("possibleUpgrades", parse_buildings),
        "queueable_upgrades": MappedValue("queueableUpgrades",
                                          parse_buildings),
        "possible_productions": MappedValue("possibleProductions",
                                            parse_productions),
        "queueable_productions": MappedValue("queueableProductions",
                                             parse_productions),
    }
