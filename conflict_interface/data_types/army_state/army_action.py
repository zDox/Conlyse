from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from dataclasses import dataclass

from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.action import Action
if TYPE_CHECKING:
    from conflict_interface.data_types.army_state.army import Army

class ArmyActionResult(Enum):
    """
    Represents potential outcomes or results of an action performed by an army.

    Attributes:
        Ok (int): Indicates the action was successful.
        OutOfRange (int): Indicates the action was not executed due to the target being out of range.
        InvalidCommandForUnitTypes (int): Indicates the action was not executed as the army is not the correct type for the command.
        NoActiveCommand (int): Indicates no command could be canceled as there is no active command.
        InvalidCommandQueue (int): Indicates the command cannot be queued as the queue would then be invalid.
            For example, if the last command of the army is an attack command. Then the next one can't be a GotoCommand.
    """
    Ok = 0
    OutOfRange = 1
    InvalidCommandForUnitTypes = 2
    NoActiveCommand = 3
    InvalidCommandQueue = 4

@dataclass
class ArmyAction(Action):
    C = "ultshared.action.UltArmyAction"
    armies: LinkedList[Army]

    MAPPING = {
        "armies": "armies",
    }