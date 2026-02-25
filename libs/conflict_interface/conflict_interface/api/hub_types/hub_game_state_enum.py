from enum import Enum

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.utils.enums import DefaultEnumMeta


@conflict_serializable(SerializationCategory.ENUM, version = -1)
class HubGameState(Enum, metaclass=DefaultEnumMeta):
    UNDEFINED = "undefined"
    NONE = "none"
    READY_TO_JOIN = "readytojoin"
    RUNNING = "running"
    FINISHED = "finished"
