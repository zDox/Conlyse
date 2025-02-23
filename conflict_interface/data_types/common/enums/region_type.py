from enum import Enum

from conflict_interface.utils import DefaultEnumMeta


class RegionType(Enum, metaclass=DefaultEnumMeta):
    NONE = -1
    EUROPA = 0
    ASIA = 1
    AFRICA = 2
    NORTH_AMERICA = 3
    SOUTH_AMERICA = 4
    OCEANIA = 5