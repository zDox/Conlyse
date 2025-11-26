from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode


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


def state_update(self: "State", other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
    if not isinstance(other, self.__class__):
        raise ValueError(f"UPDATE ERROR: Cannot update  {self.__class__} with object of type: {type(other)}")

    for attr in ["state_id", "state_type", "time_stamp"]:
        if getattr(self, attr) != getattr(other, attr):
            if rp:
                rp.replace(path + [attr], getattr(self, attr), getattr(other, attr))
            setattr(self, attr, getattr(other, attr))


def universal_update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
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

def partial_universal_update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
    """
    Function should be overwritten if some of the attributes are not always set by conflict of nations.
    This functions assumes that always the entire state is supplied.
    """
    if not isinstance(other, self.__class__):
        raise ValueError(f"UPDATE ERROR: Cannot update  {self.__class__} with object of type: {type(other)}")
    for attr in self.get_mapping().keys():
        if getattr(other, attr) is None:
            continue
        if getattr(self, attr) != getattr(other, attr):
            if rp:
                rp.replace(path + [attr], getattr(self, attr), getattr(other, attr))
            setattr(self, attr, getattr(other, attr))