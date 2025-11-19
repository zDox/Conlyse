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

from typing import Any
from typing import TYPE_CHECKING
from typing import Union
from typing import get_args
from typing import get_origin

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object import get_inner_type
from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import AddOperation
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
                    obj.pop(int(pos))
            elif issubclass(inner_type, dict):
                if pos in obj.keys():
                    obj.pop(pos)
                else:
                    logger.warning(f"Key {pos} not in {str(obj)[:100]}")
            else:
                raise ValueError(f"Can only remove from List or Dict not {type(obj)}")