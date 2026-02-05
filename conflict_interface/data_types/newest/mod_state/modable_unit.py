from dataclasses import dataclass

from conflict_interface.data_types.army_state.unit import Unit
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
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