from enum import Enum

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.ENUM, version = VERSION)
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
