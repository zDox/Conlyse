from enum import Enum

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable


@binary_serializable(SerializationCategory.ENUM)
class ResearchActionResult(Enum):
    Ok = 0
    FullResearchSlots = 1
    AlreadyCompleted = 2
    InsufficientRequirements = 3
    NotAvailable = 4
