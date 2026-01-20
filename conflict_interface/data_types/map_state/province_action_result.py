from enum import Enum

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.ENUM)
class UpdateProvinceActionResult(Enum):
    Ok = 0
    NoProduction = 1
    NoConstruction = 2
    InsufficientResources = 3
    AlreadyConstructingUpgrade = 4
    AlreadyMobilizingUnit = 5
    UpgradeNotAvailable = 6
    UnitNotAvailable = 7
    NotDemolishable = 8
