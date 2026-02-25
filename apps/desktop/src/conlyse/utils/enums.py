from enum import Enum, auto
from enum import StrEnum


class PageType(Enum):
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
    ARMY_INFO = auto()
    
    # Right sidebar panels
    EVENTS = auto()
    CITY_LIST = auto()
    ARMY_LIST = auto()
    
    # Bottom panel options
    TIMELINE = auto()