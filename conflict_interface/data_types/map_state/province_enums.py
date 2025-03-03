from enum import Enum
from enum import Enum

from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType
from conflict_interface.data_types import ResourceType

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.custom_types import DefaultEnumMeta


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

    def to_py(self, type):
        if type != ResourceType:
            raise ValueError(f"type ({type}) must be ResourceType")
        if self.value == 0:
            return ResourceType(0)
        return ResourceType(self.value - 1)
