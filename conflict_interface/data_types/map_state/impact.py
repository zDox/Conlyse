from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable
from conflict_interface.data_types.map_state.map_state_enums import ImpactType
from conflict_interface.data_types.point import Point

@binary_serializable(SerializationCategory.DATACLASS)
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