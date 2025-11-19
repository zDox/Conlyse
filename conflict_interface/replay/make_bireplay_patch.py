from __future__ import annotations

from enum import Enum
from typing import Any

from conflict_interface.data_types.custom_types import ProductionList
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object import SIMPLE_PARSE_MAPPING
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import ReplayPatch


def make_bireplay_patch(self: Any, other: Any) -> BidirectionalReplayPatch:
    """
    Create a bidirectional replay patch between two objects.

    Generates both forward and backward patches by comparing two objects,
    allowing efficient time travel in both directions.

    Args:
        self: The starting object state
        other: The ending object state

    Returns:
        A BidirectionalReplayPatch containing both forward and backward patches
    """
    forward = make_replay_patch(self, other)
    backward = make_replay_patch(other, self)
    return BidirectionalReplayPatch.from_existing_patches(forward, backward)


def make_replay_patch(self: Any, other: Any) -> ReplayPatch:
    """
    Create a replay patch representing the difference between two objects.

    Compares two objects and generates a patch that, when applied to self,
    will transform it into other.

    Args:
        self: The starting object state
        other: The target object state

    Returns:
        A ReplayPatch containing operations to transform self into other
    """
    rp = ReplayPatch()
    path = []
    make_replay_patch_any(rp, path, self, other)
    return rp


def make_replay_patch_any(rp: ReplayPatch, path: list[str], self: Any, other: Any):
    """
    Recursively build a patch by comparing two objects of any type.

    Dispatches to type-specific patch builders based on the object types.
    Handles GameObjects, lists, dicts, enums, and simple types.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        self: Current value in the starting state
        other: Current value in the target state

    Raises:
        Exception: If an unsupported type is encountered
    """
    if type(self) != type(other):
        rp.replace_op(path, dump_any(other))
    elif isinstance(other, GameObject):
        make_replay_patch_gameobject(rp, path, self, other)
    elif isinstance(other, list):
        make_replay_patch_list(rp, path, self, other)
    elif isinstance(other, dict):
        make_replay_patch_dict(rp, path, self, other)
    elif type(other) in SIMPLE_PARSE_MAPPING or isinstance(other, Enum):
        make_replay_patch_simple(rp, path, self, other)
    elif self is None and other is None:
        return
    else:
        raise Exception(f"Unsupported type {type(other)}")


def make_replay_patch_gameobject(rp: ReplayPatch, path: list[str], self, other: "GameObject"):
    """
    Build patch for changes in a GameObject.

    Iterates through all attributes of the GameObject and recursively
    compares them.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        self: Starting GameObject state
        other: Target GameObject state

    Raises:
        ValueError: If other is not a GameObject
    """
    if not isinstance(other, GameObject):
        raise ValueError(f"Can't record {type(self)} with {type(other)} not a game object")

    for key in self.get_mapping().keys():
        make_replay_patch_any(rp, path + [key], getattr(self, key), getattr(other, key))


def make_replay_patch_list(rp: ReplayPatch, path: list[str], self: list[Any], other: list[Any]):
    """
    Build patch for changes in a list.

    Handles special cases for lists of GameObjects without IDs and ProductionLists.
    For regular lists, generates add/remove/replace operations for each element.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        self: Starting list state
        other: Target list state
    """
    # Special cases where either list of GameObject and they don't have an id. Or ProductionList
    if len(other) != 0:
        if isinstance(other[0], GameObject) and not hasattr(other[0], "id"):
            if self != other:
                rp.replace_op(path, dump_any(other))
                return
        elif isinstance(other, ProductionList):
            if self != other:
                rp.replace_op(path, dump_any(other))
                return

    # Compare element-by-element
    if len(self) >= len(other):
        for index in range(len(other)):
            if self[index] != other[index]:
                make_replay_patch_any(rp, path + [index], self[index], other[index])
        for index in range(len(self)-1, len(other)-1, -1):
            rp.remove_op(path + [index])
    else:
        for index in range(len(self)):
            if self[index] != other[index]:
                make_replay_patch_any(rp, path + [index], self[index], other[index])
        for index in range(len(self), len(other)):
            rp.add_op(path + [index], dump_any(other[index]))


def make_replay_patch_dict(rp: ReplayPatch, path: list[str], self: dict[Any, Any], other: dict[Any, Any]):
    """
    Build patch for changes in a dictionary.

    Compares keys and values between two dicts, generating add/remove/replace
    operations as needed.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        self: Starting dict state
        other: Target dict state
    """
    removed_keys = set(self.keys())
    for item_key, item_value in other.items():
        if item_key in removed_keys:
            removed_keys.remove(item_key)

        if item_key not in self:
            rp.add_op(path + [dump_any(item_key)], dump_any(item_value))
        elif self.get(item_key) != item_value:
            make_replay_patch_any(rp, path + [dump_any(item_key)], self[item_key], item_value)

    for removed_key in removed_keys:
        rp.remove_op(path + [removed_key])


def make_replay_patch_simple(rp: ReplayPatch, path: list[str], self: Any, other: Any):
    """
    Build patch for simple value changes.

    Handles primitive types (int, str, bool, etc.) and enums.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        self: Starting value
        other: Target value
    """
    if self != other:
        rp.replace_op(path, dump_any(other))
