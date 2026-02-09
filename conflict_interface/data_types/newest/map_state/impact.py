from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.data_types.map_state.map_state_enums import ImpactType
from conflict_interface.data_types.point import Point

from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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