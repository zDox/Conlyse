from enum import Enum

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
