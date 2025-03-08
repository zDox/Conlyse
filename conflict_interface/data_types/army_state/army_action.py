from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.action import Action

if TYPE_CHECKING:
    from conflict_interface.data_types.army_state.army import Army


@dataclass
class ArmyAction(Action):
    C = "ultshared.action.UltArmyAction"
    armies: LinkedList[Army]

    MAPPING = {
        "armies": "armies",
    }