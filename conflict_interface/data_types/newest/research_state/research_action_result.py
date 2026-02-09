from enum import Enum

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
class ResearchActionResult(Enum):
    Ok = 0
    FullResearchSlots = 1
    AlreadyCompleted = 2
    InsufficientRequirements = 3
    NotAvailable = 4
