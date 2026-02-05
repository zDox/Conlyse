from __future__ import annotations

from enum import Enum
from typing import Any

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.data_types.game_object_json import SIMPLE_PARSE_MAPPING
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch


def make_bireplay_patch(original: Any, other: Any) -> BidirectionalReplayPatch:
    """
    Create a replay patch representing the difference between two objects.

    Compares two objects and generates a patch that, when applied to self,
    will transform it into other.

    Args:
        original: The starting object state
        other: The target object state

    Returns:
        A ReplayPatch containing operations to transform self into other
    """
    rp = BidirectionalReplayPatch()
    path = []
    make_replay_patch_any(rp, path, original, other)
    return rp


def make_replay_patch_any(rp: BidirectionalReplayPatch, path: list[str], original: Any, other: Any):
    """
    Recursively build a patch by comparing two objects of any type.

    Dispatches to type-specific patch builders based on the object types.
    Handles GameObjects, lists, dicts, enums, and simple types.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        original: Current value in the starting state
        other: Current value in the target state

    Raises:
        Exception: If an unsupported type is encountered
    """
    if type(original) != type(other):
        rp.replace(path, original, other)
    elif isinstance(other, GameObject):
        make_replay_patch_gameobject(rp, path, original, other)
    elif isinstance(other, list):
        make_replay_patch_list(rp, path, original, other)
    elif isinstance(other, dict):
        make_replay_patch_dict(rp, path, original, other)
    elif type(other) in SIMPLE_PARSE_MAPPING or isinstance(other, Enum):
        make_replay_patch_simple(rp, path, original, other)
    elif original is None and other is None:
        return
    else:
        raise Exception(f"Unsupported type {type(other)}")


def make_replay_patch_gameobject(rp:  BidirectionalReplayPatch, path: list[str], original, other: "GameObject"):
    """
    Build patch for changes in a GameObject.

    Iterates through all attributes of the GameObject and recursively
    compares them.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        original: Starting GameObject state
        other: Target GameObject state

    Raises:
        ValueError: If other is not a GameObject
    """
    if not isinstance(other, GameObject):
        raise ValueError(f"Can't record {type(original)} with {type(other)} not a game object")

    for key in original.get_mapping().keys():
        make_replay_patch_any(rp, path + [key], getattr(original, key), getattr(other, key))


def make_replay_patch_list(rp: BidirectionalReplayPatch, path: list[str], original: list[Any], other: list[Any]):
    """
    Build patch for changes in a list.

    Handles special cases for lists of GameObjects without IDs and ProductionLists.
    For regular lists, generates add/remove/replace operations for each element.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        original: Starting list state
        other: Target list state
    """
    min_length = min(len(original), len(other))
    for i in range(min_length):
        if original[i] != other[i]:
            make_replay_patch_any(rp, path + [i], original[i], other[i])
    if len(other) > len(original):
        for i in range(len(original), len(other)):
            rp.add(path + [i],  other[i])
    elif len(original) > len(other):
        for i in range(len(original) - 1, len(other) - 1, -1):
            rp.remove(path + [i], original[i])



def make_replay_patch_dict(rp: BidirectionalReplayPatch, path: list[str], original: dict[Any, Any], other: dict[Any, Any]):
    """
    Build patch for changes in a dictionary.

    Compares keys and values between two dicts, generating add/remove/replace
    operations as needed.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        original: Starting dict state
        other: Target dict state
    """
    removed_keys = set(original.keys())
    for item_key, item_value in other.items():
        str_item_key = item_key
        if type(item_key) not in (int, str):
            if isinstance(item_key, Enum):
                str_item_key = item_key.value
            else:
                raise TypeError("Dict Key is neither int,str nor enum")

        if item_key in removed_keys:
            removed_keys.remove(item_key)

        if item_key not in original:
            rp.add(path + [str_item_key], item_value)
        elif original.get(item_key) != item_value:
            make_replay_patch_any(rp, path + [str_item_key], original[item_key], item_value)

    for removed_key in removed_keys:
        str_removed_key = removed_key
        if type(removed_key) not in (int, str):
            if isinstance(removed_key, Enum):
                str_removed_key = removed_key.value
            else:
                raise TypeError("Dict Key is neither int,str nor enum")
        rp.remove(path + [str_removed_key], original[removed_key])


def make_replay_patch_simple(rp: BidirectionalReplayPatch, path: list[str], original: Any, other: Any):
    """
    Build patch for simple value changes.

    Handles primitive types (int, str, bool, etc.) and enums.

    Args:
        rp: The replay patch being built
        path: Current path in the object hierarchy
        original: Starting value
        other: Target value
    """
    if original != other:
        rp.replace(path, original, other)
