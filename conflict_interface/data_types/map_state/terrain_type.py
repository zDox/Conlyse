from enum import Enum


class TerrainType(Enum):
    """
    The type of terrain a province is.
    """
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
