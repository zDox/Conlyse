from data_types.utils import JsonMappedClass, MappedValue

from dataclasses import dataclass
from enum import Enum


class RelationType(Enum):
    TRADE_EMBARGO = 0
    PEACE = 1
    RIGHT_OF_WAY = 3
    MILITARY_PACT = 4
    SHARED_INTELLIGENCE = 6
    ARMY_COMMAND = 7
    WAR = -2
