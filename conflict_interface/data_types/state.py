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
        self.time_stamp = other.time_stamp
        self.state_id = other.state_id
        self.state_type = other.state_type
        if rp:
            rp.replace(path + ["time_stamp"], self.time_stamp, other.time_stamp)
            rp.replace(path + ["state_id"], self.state_id, other.state_id)
            if self.state_type != self.state_type:
                rp.replace(path + ["state_type"], self.state_type, other.state_type)