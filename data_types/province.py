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
    NONE: -1
    OCCUPIED_PROVINCE: 51
    MAINLAND_PROVINCE: 52
    OCCUPIED_CITY: 53
    ANNEXED_CITY: 54
    MAINLAND_CITY: 54


class ResourceProductionType(Enum):
    NONE: -1
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


class Region(Enum):
    NONE: -1
    EUROPA: 0
    ASIA: 1
    AFRICA: 2
    NORTH_AMERICA: 3
    SOUTH_AMERICA: 4
    OCEANIA: 5


@dataclass
class Building():
    healh: int
    harbour_x: int
    harbour_y: int
    upgrade_id: int


def rg_to_region(value):
    return Region(value[0])


def position_to_tuple(value):
    return (value["x"], value["y"])


@dataclass
class Province:
    # Static Data
    id: int
    name: str
    terrain_type: TerrainType
    resource_production_typ: ResourceProductionType
    adjacent_to_water: bool
    legal_owner: int
    region: Region
    center_coordinate: tuple(int, int)

    # Dynamic Data
    province_state_id: ProvinceStateID
    resource_production: int
    money_production: int
    victory_points: int
    owner_id: int
    morale: int
    buildings: list[Building]

    @classmethod
    def from_static(cls, obj):
        json_to_class_mapping = {
            "id": "id",
            "rg": ["region", rg_to_region],
            "tt": ["terrain_type", TerrainType],
            "c": ["center_coordinate", position_to_tuple],
        }
        parsed_data = {}
        for key, mapping in json_to_class_mapping.items():
            if isinstance(mapping, list):
                value = obj.get(key) if obj.get(key) else -1
                parsed_data[mapping[0]] = mapping[1](value)
            elif cls.__annotations__[mapping[0]] == bool:
                parsed_data[mapping] = bool(value)
            elif cls.__annotations__[mapping[0]] == int:
                parsed_data[mapping] = int(obj[key])
            elif cls.__annotations__[mapping[0]] == str:
                parsed_data[mapping] = str(obj[key])
        return cls(**parsed_data)

    def set_dynamic(self, obj):
        json_to_class_mapping = {
            "id": "id",
            "n": "name",
            "c": "adjacent_to_water",
            "o": "owner_id",
            "m": "morale",
            "pst": "province_state_id",
            "rp": "resource_production",
            "tp": "money_production",
            "lo": "legal_owner",
        }
        for key, value in json_to_class_mapping.items():
            if isinstance(value, list):
                self[value[0]] = value[1](obj[key])
            elif self[value[0]] == bool:
                self[value] = bool(obj[key])
            elif self[value[0]] == int:
                self[value] = int(obj[key])
            elif self[value[0]] == str:
                self[value] = str(obj[key])
