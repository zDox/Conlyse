from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from conflict_interface.data_types.game_object import GameObject

@dataclass
class State(GameObject):
    time_stamp: Optional[datetime]
    state_id: str
    state_type: int
    MAPPING = {
        "state_id": "stateID",
        "state_type": "stateType",
        "time_stamp": "timeStamp",
    }