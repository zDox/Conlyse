from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.ENUM, version = VERSION)
class FightStatus(Enum, metaclass=DefaultEnumMeta):
    """
    Status of an army.
    """
    IDLE = 0
    FIGHTING = 1
    BOMBARDING = 2
    PATROLLING = 3
    APPROACH_PATROL = 4
    SIEGING = 5
    ANTI_AIR = 6
    BOMBING = 7

from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.ENUM, version = VERSION)
class Aggressiveness(Enum, metaclass=DefaultEnumMeta):
    """
    Represents under which situations a unit would engage an enemy.
    """
    DEFAULT = 0
    HOLD_FIRE = 1
    RETURN_FIRE = 2
    NORMAL = 3
    AGGRESSIVE = 4

from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.ENUM, version = VERSION)
class ForcedMarch(Enum, metaclass=DefaultEnumMeta):
    """
    ForcedMarch is the march where a unit gets a bit of damage
    but in turn is a little bit faster.
    """
    DEACTIVE = 0
    ACTIVE = 1
    PREMIUM = 2

from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.ENUM, version = VERSION)
class MissileType(Enum, metaclass=DefaultEnumMeta):
    BALLISTIC = 1
    CRUISE = 2
