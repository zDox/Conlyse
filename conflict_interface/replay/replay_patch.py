"""
Replay patch operations for tracking changes to game state.

This module defines the operations used to represent changes between game states
in the replay system. It supports three types of operations: Add, Replace, and Remove.
"""
from dataclasses import dataclass
from typing import Any

from conflict_interface.logger_config import get_logger
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import PathNode
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION

logger = get_logger()

@dataclass
class ReplayPatch:
    op_types: list[int]
    paths: list[list[PathNode]]
    values: list[Any]


class BidirectionalReplayPatch:
    """
    A pair of patches for forward and backward time travel in replays.

    This class maintains two patches: one for moving forward in time and one for
    moving backward. This allows efficient bidirectional navigation through replay
    history without storing complete game states at each timestamp.
    """

    def __init__(self):
        """Initialize with empty forward and backward patches."""
        self.forward_patch = ReplayPatch([],[],[])
        self.backward_patch = ReplayPatch([],[],[])

    def add(self, path: list[PathNode], new_value: Any) -> None:
        """
        Record an add operation in both directions.

        Forward: add new_value, Backward: remove it

        Args:
            path: JSON path where the value is added
            new_value: The value being added
        """
        self.forward_patch.op_types.append(ADD_OPERATION)
        self.forward_patch.paths.append(path)
        self.forward_patch.values.append(new_value)

        self.backward_patch.op_types.append(REMOVE_OPERATION)
        self.backward_patch.paths.append(path)
        self.backward_patch.values.append(None)

    def replace(self, path: list[str], old_value: Any, new_value: Any) -> None:
        """
        Record a replace operation in both directions.

        Forward: replace with new_value, Backward: replace with old_value

        Args:
            path: JSON path to the value being replaced
            old_value: The current value before replacement
            new_value: The new value after replacement
        """
        self.forward_patch.op_types.append(REPLACE_OPERATION)
        self.forward_patch.paths.append(path)
        self.forward_patch.values.append(new_value)

        self.backward_patch.op_types.append(REPLACE_OPERATION)
        self.backward_patch.paths.append(path)
        self.backward_patch.values.append(old_value)

    def remove(self, path: list[str], old_value: Any) -> None:
        """
        Record a remove operation in both directions.

        Forward: remove the value, Backward: add it back

        Args:
            path: JSON path to the value being removed
            old_value: The value being removed (needed to restore it when going backward)
        """
        self.forward_patch.op_types.append(REMOVE_OPERATION)
        self.forward_patch.paths.append(path)
        self.forward_patch.values.append(None)

        self.backward_patch.op_types.append(ADD_OPERATION)
        self.backward_patch.paths.append(path)
        self.backward_patch.values.append(old_value)