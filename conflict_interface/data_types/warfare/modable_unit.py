
from conflict_interface.utils import GameObject

from dataclasses import dataclass

from conflict_interface.utils import MappedValue

from .unit import Unit


def parse_unit(obj):
    if obj is None:
        return
    return Unit.from_dict(obj)


@dataclass
class SpecialUnit(GameObject):
    enabled: bool
    constructing: bool
    unit: Unit
    original_unit: Unit

    MAPPING = {
        "enabled": "e",
        "constructing": "cn",
        "unit": MappedValue("unit", parse_unit),
        "original_unit": MappedValue("originalUnit", parse_unit),
    }
