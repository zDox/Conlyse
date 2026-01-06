from enum import Enum
from enum import auto


class ReplayHookTag(Enum):
    ProvinceChanged = auto()
    PlayerChanged = auto()
    TeamChanged = auto()
    ArmyChanged = auto()
    GameInfoChanged = auto()