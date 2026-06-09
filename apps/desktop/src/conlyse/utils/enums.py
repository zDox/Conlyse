from enum import Enum, auto
from enum import StrEnum


class PageType(Enum):
    AuthPage = auto()
    ReplayListPage = auto()
    DashBoardPage = auto()
    ProvinceListPage = auto()
    CountryListPage = auto()
    MapPage = auto()
    ReplayLoadPage = auto()
    PlayerListPage = auto()
    SettingsPage = auto()

class Theme(StrEnum):
    LIGHT = "LIGHT"
    DARK = "DARK"

class DockType(Enum):
    """Types of panels available in ReplayPage sidebars and bottom panel."""
    # Left sidebar panels
    GAME_INFO = auto()
    PROVINCE_INFO = auto()
    WIN_PROBABILITY = auto()

    # Right sidebar panels
    CITY_LIST = auto()

    # Bottom panel options
    TIMELINE = auto()