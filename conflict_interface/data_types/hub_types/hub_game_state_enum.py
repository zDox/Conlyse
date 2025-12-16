from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
class HubGameState(Enum, metaclass=DefaultEnumMeta):
    UNDEFINED = "undefined"
    NONE = "none"
    READY_TO_JOIN = "readytojoin"
    RUNNING = "running"
    FINISHED = "finished"
