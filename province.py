from dataclasses import dataclass
from enum import Enum


class TerrainType(Enum):
    PLAINS: 10
    HILLS: 11
    MOUNTIN: 12
    FOREST: 13
    URBAN: 14
    JUNGLE: 15
    TUNDRA: 16
    DESERT: 17
    SEA: 18
    HIGHSEA: 19
    COASTAL: 20
    SUBURBAN: 21


class ProvinceStateID(Enum):
    NONE: 0
    OCCUPIED_PROVINCE: 51
    MAINLAND_PROVINCE: 52
    OCCUPIED_CITY: 53
    ANNEXED_CITY: 54
    MAINLAND_CITY: 54


class ResourceProductionType(Enum):
    SUPPLIES: 1
    COMPONENTS: 2
    MANPOWER: 3
    RARE_MATERIALS: 4
    FUEL: 5
    ELECTRONICS: 6
    CONVENTIONAL_WARHEAD: 8
    CHEMICAL_WARHEAD: 8
    NUCLEAR_WARHEAD: 9
    DEPLOYABLE_GEAR: 10
    MONEY: 20


class Building(Enum):
    pass


@dataclass
class Province:
    province_id: int
    name: str
    terrain_type: TerrainType
    province_state_id: ProvinceStateID
    resource_production: int
    resource_production_typ: ResourceProductionType
    victory_points: int
    adjacent_to_water: bool
    legal_owner: int
    buildings: list[Building]
