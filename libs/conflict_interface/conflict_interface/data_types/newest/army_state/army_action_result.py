from enum import Enum

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
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
