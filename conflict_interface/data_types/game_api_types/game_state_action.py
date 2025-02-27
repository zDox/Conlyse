from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from conflict_interface.data_types import GameObject, LinkedList, HashMap

"@c": "ultshared.action.UltUpdateGameStateAction",
            "stateType": 0,
            "stateID": "0",
            "addStateIDsOnSent": True,
            "option": None,
            "stateIDs": self.state_ids,
            "tstamps": self.time_stamps,

@dataclass
class GameStateAction(GameObject):
    C = "ultshared.action.UltUpdateGameStateAction"
    state_type: int
    state_id: str
    add_state_ids_on_sent: bool
    option: Any
    state_ids: HashMap[int, str]
    time_stamps: HashMap[int, datetime]
    actions: Optional[LinkedList[GameObject]]

    MAPPING = {
        "state_type": "stateType",
        "state_id": "stateID",
        "add_state_ids_on_sent": "addStateIDsOnSent",
        "option": "option",
        "state_ids": "stateIDs",
        "time_stamps": "tstamps",
        "actions": "actions"
    }
