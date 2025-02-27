from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta


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

class TerrainTypeStr(Enum, metaclass=DefaultEnumMeta):
    """
    The type of terrain a province is.
    """
    NONE = "NONE"
    PLAINS = "PLAINS"
    HILLS = "HILLS"
    MOUNTAIN = "MOUNTAIN"
    FOREST = "FOREST"
    URBAN = "URBAN"
    JUNGLE = "JUNGLE"
    TUNDRA = "TUNDRA"
    DESERT = "DESERT"
    SEA = "SEA"
    HIGHSEA = "HIGHSEA"
    COASTAL = "COASTAL"
    SUBURBAN = "SUBURBAN"
