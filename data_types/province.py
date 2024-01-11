from data_types.utils import MappedValue

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

    static_mapping = {
        "id": "id",
        "rg": MappedValue("region", rg_to_region),
        "tt": "terrain_type",
        "c": MappedValue("center_coordinate", position_to_tuple),
    }

    dynamic_mapping = {
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

    @classmethod
    def from_static(cls, obj):
        parsed_data = {}
        for new_name, mapped_value in cls.static_mapping.items():
            if not isinstance(mapped_value, MappedValue):
                if obj.get(mapped_value) is None:
                    parsed_data[new_name] = None
                else:
                    parsed_data[new_name] = cls.__annotations__[new_name](
                            obj.get(mapped_value))
                continue

            if mapped_value.function:
                if mapped_value.needs_entire_obj:
                    parsed_data[new_name] = mapped_value.function(
                            obj, obj.get(mapped_value.original))
                else:
                    parsed_data[new_name] = mapped_value.function(
                            obj.get(mapped_value.original))
            else:
                parsed_data[new_name] = cls.__annotations__[new_name](
                        obj.get(mapped_value.original))
        return cls(**parsed_data)

    def set_dynamic(self, obj):
        for new_name, mapped_value in self.dynamic_mapping.items():
            if not isinstance(mapped_value, MappedValue):
                if obj.get(mapped_value) is None:
                    self[new_name] = None
                else:
                    self[new_name] = self.__annotations__[new_name](
                            obj.get(mapped_value))
                continue

            if mapped_value.function:
                if mapped_value.needs_entire_obj:
                    self[new_name] = mapped_value.function(
                            obj, obj.get(mapped_value.original))
                else:
                    self[new_name] = mapped_value.function(
                            obj.get(mapped_value.original))
            else:
                self[new_name] = self.__annotations__[new_name](
                        obj.get(mapped_value.original))
