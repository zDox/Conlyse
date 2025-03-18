from __future__ import  annotations
from typing import Any
from typing import TYPE_CHECKING

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object import SIMPLE_PARSE_MAPPING
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
    elif obj_type in SIMPLE_PARSE_MAPPING:
        return apply_operation_simple(op, obj_type, obj)
    else:
        raise NotImplementedError("Expected is either a GameObject, List or Dict")



def apply_operation_gameobject(op: Operation, obj_type: type, obj: GameObject, game: GameInterface):
    if len(op.path) == 0:
        if isinstance(op, AddOperation):
            raise Exception(f"Cannot apply {op} on {obj}")
        elif isinstance(op, ReplaceOperation):
            raise Exception(f"Cannot apply {op} on {obj}")
        elif isinstance(op, RemoveOperation):
            return None

    if not hasattr(obj, op.path[0]):
        logger.warning(f"{obj.__class__} has no attribute '{op.path[0]}'")
        return
    key = op.path.pop(0)
    setattr(obj, key, apply_operation_any(op, obj_type.get_type_hints_cached()[key], getattr(obj, key), game))
    return obj

def apply_operation_list(op: Operation, obj_type: type, obj: list, game: GameInterface):
    if len(op.path) == 0:
        if isinstance(op, ReplaceOperation):
            obj = parse_any(obj_type, op.new_value, game)
        else:
            raise Exception(f"Operation is {op} but path is empty and obj is {obj}")
    value_type = obj_type.__args__[0]
    if len(op.path) == 1:
        if isinstance(op, AddOperation):
            obj.append(parse_any(value_type, op.new_value, game))
        elif isinstance(op, ReplaceOperation):
            obj[int(op.path[0])] = parse_any(value_type, op.new_value, game)
        else:
            raise Exception(f"RemoveOperation is not supported in list {value_type}")
    else:
        op.path.pop(0)
        apply_operation_any(op, value_type, obj[int(op.path[0])], game)
    return obj

def apply_operation_dict(op: Operation, obj_type: type, obj: dict, game: GameInterface):
    if len(op.path) == 0:
        return parse_any(type(obj), op.new_value, game)


    if len(op.path) == 1:
        key = parse_any(obj_type.__args__[0], op.path[0], game)

        if isinstance(op, AddOperation):
            value = parse_any(obj_type.__args__[1], op.new_value, game)
            obj[key] = value
        elif isinstance(op, ReplaceOperation):
            value = parse_any(obj_type.__args__[1], op.new_value, game)
            obj[key] = value
        else:
            obj.pop(key)
    else:
        op.path.pop(0)
        apply_operation_any(op, obj_type, obj[key], game)
    return obj

def apply_operation_simple(op: Operation, obj_type: type, obj: Any) -> Any:
    if len(op.path) != 0:
        raise Exception(f"Operation is {op} but path is not empty and obj is {obj}")

    if isinstance(op, AddOperation):
        raise Exception(f"Cannot apply {op} on {obj}")
    elif isinstance(op, RemoveOperation):
        raise Exception(f"Cannot apply {op} on {obj}")

    return parse_any(obj_type, op.new_value)