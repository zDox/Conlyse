from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta


class Faction(Enum, metaclass=DefaultEnumMeta):
    NONE = 0
    WESTERN = 1
    EASTERN = 2
    EUROPEAN = 3

    @property
    def code(self):
        if self.WESTERN:
            return "US"
        elif self.EASTERN:
            return "RU"
        elif self.EUROPEAN:
            return "EU"
        raise ValueError("No code for faction NONE")
