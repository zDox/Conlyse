from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import get_type_hints

from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable

if TYPE_CHECKING:
    from conflict_interface.data_types.army_state.army import Army

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class ArmyAction(Action):
    C = "ultshared.action.UltArmyAction"
    armies: LinkedList[Army]

    MAPPING = {
        "armies": "armies",
    }

    @classmethod
    def get_type_hints_cached(cls):
        if cls._type_hints is None:
            # Import Army at runtime only when type hints are needed
            from conflict_interface.data_types.army_state.army import Army
            cls._type_hints = get_type_hints(cls, localns={'Army': Army})
        return cls._type_hints