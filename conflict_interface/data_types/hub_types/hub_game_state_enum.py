from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta


class HubGameState(Enum, metaclass=DefaultEnumMeta):
    UNDEFINED = "undefined"
    NONE = "none"
    READY_TO_JOIN = "readytojoin"
    RUNNING = "running"
    FINISHED = "finished"
