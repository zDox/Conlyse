from typing import Any

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION

logger = get_logger()

def apply_operation(op_type: int, value: Any, reference: GameObject | list | dict, pos: int | str):
    """
    Apply a single operation to a game object.

    Handles three types of operations:
    - ReplaceOperation: Replace an existing value
    - AddOperation: Add a new value to a list or dict
    - RemoveOperation: Remove a value from a list, dict, or GameObject

    Args:
        op_type: The operation type to apply
        value: The value for the operation
        reference: The parent object containing the target
        pos: Position/key within the parent where operation applies

    Raises:
        ValueError: If operation type doesn't match object type
    """
    # Replace operation: Update an existing value
    if op_type == REPLACE_OPERATION:
        if isinstance(reference, GameObject):
            if not type(pos) is str:
                raise ValueError(f"Can only replace at str for gameObject but got {type(pos)}")
            if not hasattr(reference, pos):
                raise ValueError(f"Object {str(reference)[:100]}has no attribute '{pos}'")

            setattr(reference, pos, value)
        elif isinstance(reference, list) or isinstance(reference, dict):
            reference[pos] = value
        else:
            raise ValueError(f"pos is not str or int it is: {type(pos)} for {pos}")

    # Add operation: Insert a new value
    if op_type == ADD_OPERATION:
        if isinstance(reference, list):
            # Append to list
            reference.append(value)
        elif isinstance(reference, dict):
            # Add key-value pair to dict
            reference[pos] = value
        else:
            raise ValueError(f"Can only add to List or Dict not {type(reference)}")

    # Remove operation: Delete a value
    if op_type == REMOVE_OPERATION:
        if isinstance(reference, GameObject):
            if not type(pos) is str:
                raise ValueError(f"Can only remove at str for gameObject but got {type(pos)}")
            if not hasattr(reference, pos):
                raise ValueError(f"Object has no attribute '{pos}'")
            # Set attribute to None to "remove" it
            setattr(reference, pos, None)
        else:
            reference.pop(pos)

def get_child_reference(parent: GameObject | list | dict, path_element: str | int) -> GameObject | list | dict | None:
    """
    Get the child reference from a parent object based on the path element.

    Args:
        parent: The parent object (GameObject, list, or dict)
        path_element: The key/index to access the child
    Returns:
        The child reference or None if not found
    """
    if isinstance(parent, GameObject):
        if hasattr(parent, path_element):
            return getattr(parent, path_element)
        else:
            raise ValueError(f"Parent object of type {type(parent)} has no attribute '{path_element}'")
    elif isinstance(parent, list):
        if not isinstance(path_element, int) or path_element < 0 or path_element >= len(parent):
            raise IndexError(f"List index out of range: {path_element} for list of length {len(parent)}, parent is {parent}")
        return parent[path_element]
    elif isinstance(parent, dict):
        if not isinstance(path_element, (str, int)):
            raise KeyError(f"Dict key must be a string or int but got {type(path_element)}")
        if path_element not in parent:
            raise KeyError(f"Dict has no key '{path_element}' Parent is {parent}")

        return parent[path_element]
    else:
        return None

