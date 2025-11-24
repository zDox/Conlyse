"""
Hook system for tracking changes to GameObjects.

This module provides a fast and efficient system for registering callbacks
that are triggered when GameObjects are changed, added, or removed.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable
from typing import TYPE_CHECKING

from conflict_interface.logger_config import get_logger

if TYPE_CHECKING:
    from conflict_interface.replay.replay import Replay

logger = get_logger()


class ChangeType(Enum):
    """Types of changes that can trigger hooks."""
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"


@dataclass
class Hook:
    """Represents a registered hook with its pattern and callback."""
    pattern: list[str]  # Path pattern with potential wildcards
    callback: Callable
    change_types: set[ChangeType]  # Which change types trigger this hook

    def matches(self, path: int, change_type: ChangeType) -> bool:
        """
        Check if this hook matches a given path and change type.

        Wildcard rules:
        - '?' matches exactly one path element
        - '$' matches zero or more path elements (variable length)

        Args:
            path: The actual path where a change occurred
            change_type: The type of change that occurred

        Returns:
            True if this hook should be triggered for this change
        """
        if change_type not in self.change_types:
            return False

        return self._match_pattern(path)

    def _match_pattern(self, path: int) -> bool:
        """
        Recursively match pattern against path.

        Args:
            path: Path elements to match against

        Returns:
            True if pattern matches path
        """
        # Base case: both empty means match
        pattern = self.pattern
        if not pattern and not path:
            return True

        # Pattern empty but path has elements: no match
        if not pattern:
            return False

        # Path empty but pattern has elements
        if not path:
            # Only matches if remaining pattern is just '$' wildcards
            return all(p == '$' for p in pattern)

        current_pattern = pattern[0]

        if current_pattern == '$':
            # '$' can match 0 or more elements
            # Try matching with 0 elements (skip the '$')
            if self._match_pattern(pattern[1:], path):
                return True
            # Try matching with 1 or more elements (consume path element, keep '$')
            return self._match_pattern(pattern, path[1:])

        elif current_pattern == '?':
            # '?' matches exactly one element
            return self._match_pattern(pattern[1:], path[1:])

        else:
            # Literal match required
            if current_pattern == path[0]:
                return self._match_pattern(pattern[1:], path[1:])
            return False




@dataclass
class QueuedHook:
    """Represents a hook that has been queued for execution."""
    callback: Callable
    change_type: ChangeType
    path: int
    old_value: Any
    new_value: Any





class HookSystem:
    """
    Manages hook registrations and queuing for GameObject changes.
    
    The hook system allows registration of callbacks that are triggered when
    specific paths in the game state are modified. It supports wildcard patterns
    for flexible matching.
    """
    
    def __init__(self, replay: Replay | None):
        """Initialize the hook system."""
        self.hooks: list[Hook] = []
        self.queued_hooks: list[QueuedHook] = []
        self.replay = replay

        self._old_value_cache = None
        
    def register_hook(
        self, 
        path_pattern: str, 
        callback: Callable, 
        change_types: set[ChangeType] | None = None
    ) -> None:
        """
        Register a hook for a specific path pattern.
        
        Args:
            path_pattern: Dot-separated path pattern (e.g., "states.map_state.map.provinces.?")
            callback: Function to call when pattern matches
            change_types: Set of change types that trigger this hook (default: all)
        """
        if change_types is None:
            change_types = {ChangeType.ADD, ChangeType.REMOVE, ChangeType.REPLACE}
            
        pattern = path_pattern.split(".") # TODO
        hook = Hook(pattern, callback, change_types)
        self.hooks.append(hook)
        logger.debug(f"Registered hook for pattern: {path_pattern}")
        
    def queue_hook_from_operation(
        self, 
        op_type: int,
        path: int,
        new_value: Any,
        old_value: Any | None = None
    ) -> None:
        """
        Queue hooks based on a replay operation.
        
        Args:
            path:
            new_value:
            op_type:
            old_value: The old value before the operation (for replace operations)
        """

        # Determine change type
        if op_type == 1:
            change_type = ChangeType.ADD
            new_value = new_value
        elif op_type == 2:
            change_type = ChangeType.REMOVE
            new_value = None
        elif op_type == 3:
            change_type = ChangeType.REPLACE
            new_value = new_value
        else:
            logger.error(f"Unknown operation type: {op_type}")
            return

        # Find matching hooks
        for hook in self.hooks:
            if hook.matches(path, change_type):
                if op_type != 1 and self.replay:
                    old_value = self._get_old_value(path)

                queued = QueuedHook(
                    callback=hook.callback,
                    change_type=change_type,
                    path=path,
                    old_value=old_value,
                    new_value=new_value
                )
                self.queued_hooks.append(queued)

        self._old_value_cache = None # Get ready for next object

    def _get_old_value(self, path: int):
        assert(self.replay)
        if self._old_value_cache is None:
            old = self.replay.storage.path_tree.idx_to_node[path].reference
            self._old_value_cache = deepcopy(old)

        return self._old_value_cache

    def execute_queued_hooks(self) -> None:
        """
        Execute all queued hooks and clear the queue.
        
        This should be called after all updates have been applied.
        """
        hooks_to_execute = self.queued_hooks.copy()
        self.queued_hooks.clear()
        
        for queued in hooks_to_execute:
            try:
                # Call the hook with relevant information
                queued.callback(
                    change_type=queued.change_type,
                    path=queued.path,
                    old_value=queued.old_value,
                    new_value=queued.new_value
                )
            except Exception as e:
                logger.error(f"Error executing hook: {e}", exc_info=True)
                
    def clear_hooks(self) -> None:
        """Clear all registered hooks."""
        self.hooks.clear()
        logger.debug("Cleared all hooks")
        
    def clear_queue(self) -> None:
        """Clear all queued hooks without executing them."""
        self.queued_hooks.clear()
        logger.debug("Cleared hook queue")
