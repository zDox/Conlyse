from __future__ import  annotations

from enum import Enum
from typing import Any
from typing import TYPE_CHECKING

from conflict_interface.data_types.custom_types import ProductionList
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object import SIMPLE_PARSE_MAPPING
from conflict_interface.data_types.game_object import dump_any
from conflict_interface.data_types.game_object import get_inner_type
from conflict_interface.data_types.game_object import parse_any
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import Operation
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.replay.replay_patch import ReplayPatch

if TYPE_CHECKING:
    from conflict_interface.interface.game_interface import GameInterface

logger = get_logger()

def apply_patch_any(rp: ReplayPatch, obj_type: type, obj: Any, game: GameInterface):
    for op in rp.operations:
        apply_operation_any(op, obj_type, obj, game)

def apply_operation_any(op: Operation, obj_type: type, obj: Any, game: GameInterface):
    if isinstance(obj, GameObject):
        return apply_operation_gameobject(op, obj_type, obj, game)
    elif isinstance(obj, list):
        return apply_operation_list(op, obj_type, obj, game)
    elif isinstance(obj, dict):
        return apply_operation_dict(op, obj_type, obj, game)
    elif get_inner_type(obj_type, obj) in SIMPLE_PARSE_MAPPING:
        return apply_operation_simple(op, get_inner_type(obj_type, obj), obj)
    elif obj is None and len(op.path) == 0:
        return parse_any(obj_type, op.new_value, game)
    elif isinstance(obj, Enum):
        return parse_any(obj_type, op.new_value, game)
    else:
        raise NotImplementedError(f"Expected is either a GameObject, List or Dict but encountered {obj_type}")



def apply_operation_gameobject(op: Operation, obj_type: type, obj: GameObject, game: GameInterface):
    if len(op.path) == 0:
        if isinstance(op, AddOperation):
            raise Exception(f"Cannot apply {op} on {obj}")
        elif isinstance(op, ReplaceOperation):
            return parse_any(obj_type, op.new_value, game)
        elif isinstance(op, RemoveOperation):
            return None

    if not hasattr(obj, op.path[0]):
        logger.warning(f"{obj.__class__} has no attribute '{op.path[0]}'")
        return
    key = op.path.pop(0)
    setattr(obj, key, apply_operation_any(op, obj.get_type_hints_cached()[key], getattr(obj, key), game))
    return obj

def apply_operation_list(op: Operation, obj_type: type, obj: list, game: GameInterface):
    print(op, obj_type)
    if len(op.path) == 0:
        if isinstance(op, ReplaceOperation):
            return parse_any(obj_type, op.new_value, game)
        else:
            raise Exception(f"Operation is {op} but path is empty and obj is {obj}")
    value_type = obj_type.__args__[0]
    if len(op.path) == 1:
        if isinstance(op, AddOperation):
            obj.append(parse_any(value_type, op.new_value, game))
        elif isinstance(op, ReplaceOperation):
            obj[int(op.path[0])] = parse_any(value_type, op.new_value, game)
        else:
            obj.pop()
    else:
        key = op.path.pop(0)
        apply_operation_any(op, value_type, obj[int(key)], game)
    return obj

def apply_operation_dict(op: Operation, obj_type: type, obj: dict, game: GameInterface):
    if len(op.path) == 0:
        return parse_any(obj_type, op.new_value, game)


    if len(op.path) == 1:
        python_type = get_inner_type(obj_type, obj)
        print(python_type.__args__[0], op.path[0])
        key = parse_any(python_type.__args__[0], op.path[0], game)

        if isinstance(op, AddOperation):
            value = parse_any(python_type.__args__[1], op.new_value, game)
            obj[key] = value
        elif isinstance(op, ReplaceOperation):
            value = parse_any(python_type.__args__[1], op.new_value, game)
            obj[key] = value
        else:
            obj.pop(key)
    else:
        python_type = get_inner_type(obj_type, obj)
        print(f"Dict: Passing operation with key {python_type}")
        key = parse_any(python_type.__args__[0], op.path[0], game)
        op.path.pop(0)
        apply_operation_any(op, python_type.__args__[1], obj[key], game)
    return obj

def apply_operation_simple(op: Operation, obj_type: type, obj: Any) -> Any:
    if len(op.path) != 0:
        raise Exception(f"Operation is {op} but path is not empty and obj is {obj}")

    if isinstance(op, AddOperation):
        raise Exception(f"Cannot apply {op} on {obj}")
    elif isinstance(op, RemoveOperation):
        raise Exception(f"Cannot apply {op} on {obj}")

    return parse_any(obj_type, op.new_value)

def make_replay_patch(self: Any, other: Any) -> ReplayPatch:
    rp = ReplayPatch()
    path = []
    make_replay_patch_any(rp, path, self, other)
    return rp

def make_replay_patch_any(rp: ReplayPatch, path: list[str], self: Any, other: Any):
    print(self, other)
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
            print(rp.operations)
        elif self.get(item_key) != item_value:
            make_replay_patch_any(rp, path + [dump_any(item_key)], self[item_key], item_value)

    for removed_key in removed_keys:
        rp.remove_op(path + [removed_key])

def make_replay_patch_simple(rp: ReplayPatch, path: list[str], self: Any, other: Any):
    if self != other:
        rp.replace_op(path, dump_any(other))