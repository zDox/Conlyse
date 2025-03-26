from __future__ import annotations

from enum import Enum
from typing import Any
from typing import TYPE_CHECKING
from typing import Union
from typing import get_args
from typing import get_origin


from conflict_interface.data_types.custom_types import ProductionList
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object import SIMPLE_PARSE_MAPPING
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import get_inner_type
from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import Operation
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.replay.replay_patch import ReplayPatch

if TYPE_CHECKING:
    from conflict_interface.interface.game_interface import GameInterface

logger = get_logger()


def get_list_element_type(list_type_hint: type, list_element) -> type:
    """
    Takes the type hint of a list ond a list element and returns the type of the list element.
    Args:
        list_type_hint: Type hint of the list
        list_element:  Element of the list

    Returns:
        Type of the list element ready to be parsed
    """
    origin = get_origin(list_type_hint)
    args = get_args(list_type_hint)
    non_optional_list_type = list_type_hint
    json_type = type(list_element)
    if origin is Union:
        if args[0] is None:
            raise ValueError("Type is None, cant extract inner type.")
        if len(args) == 2 and args[1] is type(None):
            non_optional_list_type = args[0]

    origin = get_origin(non_optional_list_type)
    args = get_args(non_optional_list_type)
    if origin is Union:
        for arg in args:
            element_type = get_args(arg)[0]
            if element_type is None:
                raise ValueError("Type is None, cant extract inner type.")
            if json_type is dict:
                if "@c" in list_element:
                    if hasattr(element_type, "C") and element_type.C == list_element["@c"]:
                        return element_type
                elif json_type == element_type:
                    return element_type
                elif element_type.__name__ == "Point" and list_element.keys() == {"x", "y"}:
                    return element_type
            elif json_type is list:
                if hasattr(element_type, "C") and element_type.C == list_element[0]:
                    return element_type
            elif element_type is json_type:
                return element_type

    elif non_optional_list_type is None:
        raise ValueError("Type is None, cant extract inner type.")
    else:
        if len(args) == 2:
            return args[1]
        elif len(args) != 1:
            raise ValueError(f"Expected list got {non_optional_list_type} for {list_element} and typehint {list_type_hint} with args {args}")
        return args[0]

def recur_path(obj: Any, obj_type: type, path: list[str | int], game_state: GameState, game: GameInterface) -> tuple[Any, str | int, type] |tuple[Any, str | int]:
    if len(path) == 0:
        raise ValueError(f"Path is empty for {obj}")
    if len(path) == 1:
        if isinstance(obj, GameObject):
            if not hasattr(obj, path[0]):
                raise ValueError(f"Object {str(obj)[:100]} has no attribute '{path[0]}'")
            else:
                obj_type = obj.get_type_hints_cached()[path[0]]
        return obj, path[0], obj_type
    key = path.pop(0)
    if isinstance(obj, GameObject):
        if not hasattr(obj, key):
            raise ValueError(f"Object {str(obj)[:100]} has no attribute '{key}'")
        return recur_path(getattr(obj, key), obj.get_type_hints_cached()[key], path, game_state, game)
    elif isinstance(obj, list):
        return recur_path(obj[int(key)], get_args(obj_type)[0], path, game_state, game)
    elif isinstance(obj, dict):
        inner_type = get_inner_type(obj_type, obj)
        key = parse_any(get_args(inner_type)[0], key, game)
        return recur_path(obj[key], get_args(inner_type)[1], path, game_state, game)

def apply_patch_any(rp: ReplayPatch, game_state: GameState, game: GameInterface):
    if not isinstance(game_state, GameState):
        raise ValueError(f"Expected game state but got {type(game_state)}")
    for op in rp.operations:
        obj, pos, obj_type = recur_path(game_state, GameState, op.path.copy(), game_state, game)
        apply_operation(op, obj, obj_type, pos, game)

def apply_operation(op: Operation, obj: GameObject | list | dict, obj_type, pos: int | str,  game):
    if isinstance(op, ReplaceOperation):
        if isinstance(obj, GameObject):
            if not type(pos) is str:
                raise ValueError(f"Can only replace at str for gameObject but got {type(pos)}")
            if not hasattr(obj, pos):
                raise ValueError(f"Object {str(obj)[:100]}has no attribute '{pos}'")
            inner_type = get_inner_type(obj_type, op.new_value)
            setattr(obj, pos, parse_any(inner_type, op.new_value, game))
        elif isinstance(obj, list) or isinstance(obj, dict):
            ele_type = get_list_element_type(obj_type, op.new_value)
            obj[pos] = parse_any(ele_type, op.new_value, game)
        else:
            raise ValueError(f"pos is not str or int it is: {type(pos)} for {pos}")

    if isinstance(op, AddOperation):
        if isinstance(obj, list):
            obj.append(parse_any(get_list_element_type(obj_type, op.new_value), op.new_value, game))
        elif isinstance(obj, dict):
            inner_type = get_inner_type(obj_type, obj)
            key = parse_any(get_args(inner_type)[0], pos, game)
            obj[key] = parse_any(get_args(inner_type)[1], op.new_value, game)
        else:
            raise ValueError(f"Can only add to List or Dict not {type(obj)}")

    if isinstance(op, RemoveOperation):
        if isinstance(obj, GameObject):
            if not type(pos) is str:
                raise ValueError(f"Can only remove at str for gameObject but got {type(pos)}")
            if not hasattr(obj,pos):
                raise ValueError(f"Object has no attribute '{pos}'")
            setattr(obj, pos, None)
        else:
            if type(obj) is list:
                obj.pop()
            elif type(obj) is dict:
                obj.pop(pos)

def make_bireplay_patch(self: Any, other: Any) -> BidirectionalReplayPatch:
    forward = make_replay_patch(self, other)
    backward = make_replay_patch(other, self)
    return BidirectionalReplayPatch.from_existing_patches(forward, backward)

def make_replay_patch(self: Any, other: Any) -> ReplayPatch:
    rp = ReplayPatch()
    path = []
    make_replay_patch_any(rp, path, self, other)
    return rp

def make_replay_patch_any(rp: ReplayPatch, path: list[str], self: Any, other: Any):
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
    if not isinstance(other, GameObject):
        raise ValueError(f"Can't record {type(self)} with {type(other)} not a game object")


    for key in self.get_mapping().keys():
        make_replay_patch_any(rp, path + [key], getattr(self, key), getattr(other, key))

def make_replay_patch_list(rp: ReplayPatch, path: list[str], self: list[Any], other: list[Any]):
    # Special cases where either list of GameObject and they dont have an id. Or ProductionList
    if len(other) != 0:
        if isinstance(other[0], GameObject) and not hasattr(other[0], "id"):
            if self != other:
                rp.replace_op(path, dump_any(other))
                return
        elif isinstance(other, ProductionList):
            if self != other:
                rp.replace_op(path, dump_any(other))
                return

    for index in range(max(len(self), len(other))):
        if index >= len(self):
            rp.add_op(path + [index], dump_any(other[index]))
        elif index >= len(other):
            rp.remove_op(path + [index])
        elif self[index] != other[index]:
            make_replay_patch_any(rp, path + [index], self[index], other[index])

def make_replay_patch_dict(rp: ReplayPatch, path: list[str], self: dict[Any, Any], other: dict[Any, Any]):
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
    if self != other:
        rp.replace_op(path, dump_any(other))