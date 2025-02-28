from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.point import Point

class ImpactType(Enum, metaclass=DefaultEnumMeta):
    NORMAL = 0
    DAMAGE_AIR = 1
    SEA = 2
    BUILDING = 3
    ATOMIC = 4

@dataclass
class Impact(GameObject):
    C = "im"
    pos: Point
    time: int
    type: ImpactType
    count: int

    MAPPING = {
        "pos": "pos",
        "time": "t",
        "type": "type",
        "count": "c",
    }