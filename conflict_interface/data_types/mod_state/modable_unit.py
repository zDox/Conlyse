
from conflict_interface.utils import GameObject

from dataclasses import dataclass

from conflict_interface.data_types.army_state.unit import Unit



@dataclass
class SpecialUnit(GameObject):
    enabled: bool
    constructing: bool
    unit: Unit
    original_unit: Unit

    MAPPING = {
        "enabled": "e",
        "constructing": "cn",
        "unit": "unit",
        "original_unit": "originalUnit",
    }
