from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable

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