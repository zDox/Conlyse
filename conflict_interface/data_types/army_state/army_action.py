from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from dataclasses import dataclass

from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.action import Action
if TYPE_CHECKING:
    from conflict_interface.data_types.army_state.army import Army

class ArmyActionResult(Enum):
    Ok = 0
    OutOfRange = 1
    NotAircraft = 2
    NoActiveCommand = 3

@dataclass
class ArmyAction(Action):
    C = "ultshared.action.UltArmyAction"
    armies: LinkedList[Army]

    MAPPING = {
        "armies": "armies",
    }