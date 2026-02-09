from enum import Enum

from ..custom_types import DefaultEnumMeta
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
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
