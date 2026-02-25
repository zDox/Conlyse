from enum import Enum

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
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
