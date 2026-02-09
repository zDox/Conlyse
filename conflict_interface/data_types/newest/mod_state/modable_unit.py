from dataclasses import dataclass

from ..army_state.unit import Unit
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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