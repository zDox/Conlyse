from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.ENUM)
class Faction(Enum, metaclass=DefaultEnumMeta):
    NONE = 0
    WESTERN = 1
    EASTERN = 2
    EUROPEAN = 3

    @property
    def code(self):
        if self == Faction.WESTERN:
            return "US"
        elif self == Faction.EASTERN:
            return "RU"
        elif self == Faction.EUROPEAN:
            return "EU"
        raise ValueError("No code for faction NONE")
