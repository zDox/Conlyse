"""
Apply replay patches to game state objects.

This module provides functions to:
1. Apply patches to game states to move forward/backward in time
2. Create patches by comparing two game states
3. Navigate through nested game object structures

The patch application system handles different data structures (GameObjects, lists, dicts)
and uses type hints to correctly parse and apply changes.
"""
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
    Determine the concrete type of a list element from a type hint.
    
    Handles various cases including:
    - Optional types (Union with None)
    - Union types with multiple possibilities
    - Generic list types
    - Special types like ProductionList
    
    Args:
        list_type_hint: Type hint for the list (e.g., List[int], Optional[List[GameObject]])
        list_element: An actual element from the list to help determine the type
        
    Returns:
        The concrete type to use for parsing the element
        
    Raises:
        ValueError: If type cannot be determined or is None
    """
    origin = get_origin(list_type_hint)
    args = get_args(list_type_hint)
    non_optional_list_type = list_type_hint
    json_type = type(list_element)
    
    # Handle Optional types (Union[T, None])
    if origin is Union:
        if args[0] is None:
            raise ValueError("Type is None, cant extract inner type.")
        # Strip Optional wrapper to get the actual type
        if len(args) == 2 and args[1] is type(None):
            non_optional_list_type = args[0]

    origin = get_origin(non_optional_list_type)
    args = get_args(non_optional_list_type)
    
    # Handle Union types with multiple possibilities
    if origin is Union:
        # Try to match the actual JSON type with one of the union members
        for arg in args:
            element_type = get_args(arg)[0]
            if element_type is None:
                raise ValueError("Type is None, cant extract inner type.")
            
            # Match by JSON structure
            if json_type is dict:
                # Check for class marker in JSON
                if "@c" in list_element:
                    if hasattr(element_type, "C") and element_type.C == list_element["@c"]:
                        return element_type
                # Direct type match
                elif json_type == element_type:
                    return element_type
                # Special case for Point type
                elif element_type.__name__ == "Point" and list_element.keys() == {"x", "y"}:
                    return element_type
            elif json_type is list:
                # List format with class marker as first element
                if hasattr(element_type, "C") and element_type.C == list_element[0]:
                    return element_type
            elif element_type is json_type:
                return element_type
    elif non_optional_list_type is None:
        raise ValueError("Type is None, cant extract inner type.")
    else:
        # Simple list type - extract the element type from args
        if len(args) == 2:
            return args[1]
        elif len(args) != 1:
            raise ValueError(f"Expected list got {non_optional_list_type} for {list_element} and typehint {list_type_hint} with args {args}")
        return args[0]

def recur_path(
    obj: Any, 
    obj_type: type, 
    path: list[str | int], 
    game_state: GameState, 
    game: GameInterface
) -> tuple[Any, str | int, type] | tuple[Any, str | int]:
    """
    Recursively navigate through a nested structure to reach a target location.
    
    This function follows a path through nested GameObjects, lists, and dicts
    to reach a specific location where an operation should be applied.
    
    Args:
        obj: Current object being traversed
        obj_type: Type hint for the current object
        path: Remaining path elements to traverse
        game_state: Root game state object
        game: Game interface for parsing
        
    Returns:
        Tuple of (parent_object, final_key, target_type) where the operation should be applied
        
    Raises:
        ValueError: If path is invalid or attribute doesn't exist
    """
    if len(path) == 0:
        raise ValueError(f"Path is empty for {obj}")
    if len(path) == 1:
        if isinstance(obj, GameObject):
            if not hasattr(obj, path[0]):
                raise ValueError(f"Object {str(obj)[:100]} has no attribute '{path[0]}'")
            else:
                obj_type = obj.get_type_hints_cached()[path[0]]
        return obj, path[0], obj_type
        
    # Continue recursing down the path
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
    """
    Apply a replay patch to a game state.
    
    Iterates through all operations in the patch and applies them to the game state,
    modifying it in place to reflect the changes.
    
    Args:
        rp: The replay patch containing operations to apply
        game_state: The game state to modify
        game: Game interface for parsing operations
        
    Raises:
        ValueError: If game_state is not a GameState instance
    """
    if not isinstance(game_state, GameState):
        raise ValueError(f"Expected game state but got {type(game_state)}")
    for op in rp.operations:
        obj, pos, obj_type = recur_path(game_state, GameState, op.path.copy(), game_state, game)
        if hasattr(game, '_hook_system'):
            # Store old value for hook system (before applying operation)
            old_value = None
            if isinstance(op, ReplaceOperation):
                if isinstance(obj, GameObject):
                    if hasattr(obj, pos):
                        old_value = getattr(obj, pos)
                elif isinstance(obj, (list, dict)):
                    old_value = obj.get(pos) if isinstance(obj, dict) else (obj[pos] if pos < len(obj) else None)

            # Apply the operation
            apply_operation(op, obj, obj_type, pos, game)
            game._hook_system.queue_hook_from_operation(op, old_value)
        else:
            apply_operation(op, obj, obj_type, pos, game)

def apply_operation(op: Operation, obj: GameObject | list | dict, obj_type, pos: int | str, game):
    """
    Apply a single operation to a game object.
    
    Handles three types of operations:
    - ReplaceOperation: Replace an existing value
    - AddOperation: Add a new value to a list or dict
    - RemoveOperation: Remove a value from a list, dict, or GameObject
    
    Args:
        op: The operation to apply
        obj: The parent object containing the target
        obj_type: Type hint for the parent object
        pos: Position/key within the parent where operation applies
        game: Game interface for parsing values
        
    Raises:
        ValueError: If operation type doesn't match object type
    """
    # Replace operation: Update an existing value
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

    # Add operation: Insert a new value
    if isinstance(op, AddOperation):
        if isinstance(obj, list):
            # Append to list
            obj.append(parse_any(get_list_element_type(obj_type, op.new_value), op.new_value, game))
        elif isinstance(obj, dict):
            # Add key-value pair to dict
            inner_type = get_inner_type(obj_type, obj)
            key = parse_any(get_args(inner_type)[0], pos, game)
            obj[key] = parse_any(get_args(inner_type)[1], op.new_value, game)
        else:
            raise ValueError(f"Can only add to List or Dict not {type(obj)}")

    # Remove operation: Delete a value
    if isinstance(op, RemoveOperation):
        if isinstance(obj, GameObject):
            if not type(pos) is str:
                raise ValueError(f"Can only remove at str for gameObject but got {type(pos)}")
            if not hasattr(obj, pos):
                raise ValueError(f"Object has no attribute '{pos}'")
            # Set attribute to None to "remove" it
            setattr(obj, pos, None)
        else:
            inner_type = get_inner_type(obj_type, obj)
            if issubclass(inner_type, list):
                if len(obj) == 0:
                    logger.warning(f"Cannot remove {str(obj)[:100]} from empty list")
                else:
                    # Remove last element (patches are designed to work this way)
                    obj.pop()
            elif issubclass(inner_type, dict):
                if pos in obj.keys():
                    obj.pop(pos)
                else:
                    logger.warning(f"Key {pos} not in {str(obj)[:100]}")

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

    # Compare element-by-element
    for index in range(max(len(self), len(other))):
        if index >= len(self):
            rp.add_op(path + [index], dump_any(other[index]))
        elif index >= len(other):
            rp.remove_op(path + [index])
        elif self[index] != other[index]:
            make_replay_patch_any(rp, path + [index], self[index], other[index])

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