from typing import Any

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode

def dict_update(original: dict, other: dict, path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
    for key, value in other.items():
        if key not in original:
            if rp:
                rp.add(path + [key], value)
            original[key] = value
        else:
            if original[key] != value:
                if type(original[key]) == type(other[key]) and hasattr(original[key], "update") and callable(
                        getattr(original[key], "update")) and issubclass(type(original[key]), GameObject):
                    original[key].update(other[key], path + [key], rp)
                else:
                    if rp:
                        rp.replace(path + [key], original[key], value)
                    original[key] = value
    for key in list(original.keys()):
        if key not in other:
            if rp:
                rp.remove(path + [key], original[key])
            del original[key]


def list_update(original: list, other: list, path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):

    if other is None:
        if original is None:
            return

        for i in range(len(original)-1,-1, -1):
            if rp:
                rp.remove(path + [i], original[i])
            original.pop(i)
        return

    assert original is not None, "List does not exist. Cant update it"


    min_length = min(len(original), len(other))
    for i in range(min_length):
        if original[i] != other[i]:
            if (type(original[i]) == type(other[i]) and hasattr(original[i], "update") and
                    callable(getattr(original[i], "update")) and issubclass(type(original[i]), GameObject)):
                original[i].update(other[i], path + [i], rp)
            else:
                if rp:
                    rp.replace(path + [i], original[i], other[i])
                original[i] = other[i]
    if len(other) > len(original):
        for i in range(len(original), len(other)):
            if rp:
                rp.add(path + [i], other[i])
            original.append(other[i])
    elif len(original) > len(other):
        for i in range(len(original)-1, len(other)-1, -1):
            if rp:
                rp.remove(path + [i], original[i])
            original.pop(i)


def state_update(self: "State", other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
    if not isinstance(other, self.__class__):
        raise ValueError(f"UPDATE ERROR: Cannot update  {self.__class__} with object of type: {type(other)}")

    for attr in ["state_id", "state_type", "time_stamp"]:
        if getattr(self, attr) != getattr(other, attr):
            if rp:
                rp.replace(path + [attr], getattr(self, attr), getattr(other, attr))
            setattr(self, attr, getattr(other, attr))


def universal_update(self: Any, other: Any, path: list[PathNode] = None, rp: BidirectionalReplayPatch = None) -> None:
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
