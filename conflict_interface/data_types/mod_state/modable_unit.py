


from dataclasses import dataclass

from conflict_interface.data_types.army_state.unit import Unit
from conflict_interface.data_types.game_object import GameObject


@dataclass
class SpecialUnit(GameObject):
    C = "su"
    enabled: bool
    constructing: bool
    unit: Unit
    original_unit: Unit
    built: bool
    condition: int
    e: bool  # TODO no idea what this is

    MAPPING = {
        "enabled": "enabled",
        "constructing": "cn",
        "unit": "unit",
        "original_unit": "originalUnit",
        "built": "built",
        "condition": "c",
        "e": "e",
    }