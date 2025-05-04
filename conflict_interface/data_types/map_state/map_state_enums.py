from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.resource_state.resource_state_enums import ResourceType


class ProvinceStateID(Enum, metaclass=DefaultEnumMeta):
    """
    Enumeration for representing different types of administrative areas.

    Attributes:
        OCCUPIED_PROVINCE: Represents a province under occupation.
        MAINLAND_PROVINCE: Represents a province within the mainland.
        OCCUPIED_CITY: Represents a city under occupation.
        ANNEXED_CITY: Represents a city annexed to a different territory.
        MAINLAND_CITY: Represents a city within the mainland.
    """
    NONE = 0
    OCCUPIED_PROVINCE = 51
    MAINLAND_PROVINCE = 52
    OCCUPIED_CITY = 53
    ANNEXED_CITY = 54
    MAINLAND_CITY = 55
    MAX = 99


class ResourceProductionType(Enum, metaclass=DefaultEnumMeta):
    NONE = ResourceType.NONE.value + 1
    SUPPLY = ResourceType.SUPPLY.value + 1
    COMPONENT = ResourceType.COMPONENT.value + 1
    MANPOWER = ResourceType.MANPOWER.value + 1
    RARE_MATERIAL = ResourceType.RARE_MATERIAL.value + 1
    FUEL = ResourceType.FUEL.value + 1
    ELECTRONIC = ResourceType.ELECTRONIC.value + 1
    CONVENTIONAL_WARHEAD = ResourceType.CONVENTIONAL_WARHEAD.value + 1
    CHEMICAL_WARHEAD = ResourceType.CHEMICAL_WARHEAD.value + 1
    NUCLEAR_WARHEAD = ResourceType.NUCLEAR_WARHEAD.value + 1
    DEPLOYABLE_GEAR = ResourceType.DEPLOYABLE_GEAR.value + 1
    MONEY = ResourceType.MONEY.value + 1
    CITY_CLAIM = ResourceType.CITY_CLAIM.value + 1
    PHARMACEUTICAL = ResourceType.PHARMACEUTICAL.value + 1


class RevoltSuppressionProperty(Enum):
    DEFENSE = "DEFENSE"


class ImpactType(Enum, metaclass=DefaultEnumMeta):
    NORMAL = 0
    DAMAGE_AIR = 1
    SEA = 2
    BUILDING = 3
    ATOMIC = 4


class SeaType(Enum):
    HIGH_SEA = "HIGHSEA"
    COASTAL = "COASTAL"
    RIVER = "RIVER"


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
    RIVER = "RIVER"
