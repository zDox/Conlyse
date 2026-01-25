from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class State(GameObject):
    time_stamp: Optional[DateTimeMillisecondsInt]
    state_id: str
    state_type: int
    MAPPING = {
        "state_id": "stateID",
        "state_type": "stateType",
        "time_stamp": "timeStamp",
    }
