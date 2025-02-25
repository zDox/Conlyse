from enum import Enum

from conflict_interface.utils import DefaultEnumMeta


class TerrainType(Enum, metaclass=DefaultEnumMeta):
    """
    The type of terrain a province is.
    """
    NONE = 0
    PLAINS = 10
    HILLS = 11
    MOUNTAIN = 12
    FOREST = 13
    URBAN = 14
    JUNGLE = 15
    TUNDRA = 16
    DESERT = 17
    SEA = 18
    HIGHSEA = 19
    COASTAL = 20
    SUBURBAN = 21
