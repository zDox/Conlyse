from enum import Enum

from conflict_interface.utils import DefaultEnumMeta


class ResourceType(Enum, metaclass=DefaultEnumMeta):
    NONE = 0
    SUPPLY = 1
    COMPONENT = 2
    MANPOWER = 3
    RARE_MATERIAL = 4
    FUEL = 5
    ELECTRONIC = 6
    CONVENTIONAL_WARHEAD = 7
    CHEMICAL_WARHEAD = 8
    NUCLEAR_WARHEAD = 9
    DEPLOYABLE_GEAR = 10
    MONEY = 20
    CITY_CLAIM = 30
    PHARMACEUTICAL = 40