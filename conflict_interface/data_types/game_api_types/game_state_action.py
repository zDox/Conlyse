from dataclasses import dataclass
from typing import Any, Optional
from typing import get_type_hints

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class GameStateAction:
    C = "ultshared.action.UltUpdateGameStateAction"
    state_type: int
    state_id: str
    add_state_ids_on_sent: bool
    option: Any
    state_ids: HashMap[int, str]
    time_stamps: HashMap[int, DateTimeMillisecondsInt]
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
    _type_hints = None
    @classmethod
    def get_type_hints_cached(cls):
        if cls._type_hints is None:
            cls._type_hints = get_type_hints(cls)
        return cls._type_hints
