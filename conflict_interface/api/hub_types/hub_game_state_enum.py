from enum import Enum

from ..custom_types import DefaultEnumMeta
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
class HubGameState(Enum, metaclass=DefaultEnumMeta):
    UNDEFINED = "undefined"
    NONE = "none"
    READY_TO_JOIN = "readytojoin"
    RUNNING = "running"
    FINISHED = "finished"
