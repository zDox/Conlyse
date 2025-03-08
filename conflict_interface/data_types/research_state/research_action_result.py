from enum import Enum


class ResearchActionResult(Enum):
    Ok = 0
    FullResearchSlots = 1
    AlreadyCompleted = 2
    InsufficientRequirements = 3
    NotAvailable = 4
