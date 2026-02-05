from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.ENUM, version = VERSION)
class RegionType(Enum, metaclass=DefaultEnumMeta):
    NONE = -1
    EUROPA = 0
    ASIA = 1
    AFRICA = 2
    NORTH_AMERICA = 3
    SOUTH_AMERICA = 4
    OCEANIA = 5