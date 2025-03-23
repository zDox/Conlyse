from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode
from conflict_interface.replay.replay_patch import ReplayPatch


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

    def update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        """
        Function should be overwritten if some of the attributes are not always set by conflict of nations.
        This functions assumes that always the entire state is supplied.
        """
        if not isinstance(other, self.__class__):
            raise ValueError(f"UPDATE ERROR: Cannot update  {self.__class__} with object of type: {type(other)}")
        for attr in self.get_mapping().keys():
            if getattr(self, attr) != getattr(other, attr):
                if rp:
                    rp.replace(path + [attr], getattr(self, attr), getattr(other, attr))
                setattr(self, attr, getattr(other, attr))