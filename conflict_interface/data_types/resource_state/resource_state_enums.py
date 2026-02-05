from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.ENUM, version = VERSION)
class ResourceType(Enum, metaclass=DefaultEnumMeta):
    NONE = 0
    SUPPLY = 1
    COMPONENT = 2
    MANPOWER = 3
    RARE_MATERIAL = 4
    FUEL = 5
    ELECTRONIC = 6
    CONVENTIONAL_WARHEAD = 7
    CHEMICAL_WARHEAD = 8
    NUCLEAR_WARHEAD = 9
    DEPLOYABLE_GEAR = 10
    MONEY = 20
    CITY_CLAIM = 30
    PHARMACEUTICAL = 40
    GROUND_MUNITION = 50
    SEA_MUNITION = 60
    AIR_GROUND_MUNITION = 70