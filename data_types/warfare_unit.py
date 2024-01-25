from data_types.utils import JsonMappedClass, MappedValue

from dataclasses import dataclass


@dataclass
class Unit(JsonMappedClass):
    id: int
    unit_type: int
    health: float
    size: int
    kills: int
    camoflage_replacement_unit: int
    on_sea: bool
    at_airfield: bool
    hit_points: float
    max_hit_points: int

    mapping = {
        "id": "id",
        "unit_type": "t",
        "health": "h",
        "size": "s",
        "kills": "k",
        "camoflage_replacement_unit": "cru",
        "on_sea": "os",
        "at_airfield": "aa",
        "hit_points": "hp",
        "max_hit_points": "mhp",
    }


def parse_unit(obj):
    if obj is None:
        return
    return Unit.from_dict(obj)


@dataclass
class SpecialUnit(JsonMappedClass):
    enabled: bool
    constructing: bool
    unit: Unit
    original_unit: Unit

    mapping = {
        "enabled": "e",
        "constructing": "cn",
        "unit": MappedValue("unit", parse_unit),
        "original_unit": MappedValue("originalUnit", parse_unit),
    }
