from enum import Enum, auto


class PageType(Enum):
    ReplayListPage = auto()
    DashBoardPage = auto()
    ProvinceListPage = auto()
    CountryListPage = auto()
    MapPage = auto()

class Theme(Enum):
    LIGHT = auto()
    DARK = auto()