"""
Hook system for tracking changes to GameObjects.

This module provides a fast and efficient system for registering callbacks
that are triggered when GameObjects are changed, added, or removed.
"""
from __future__ import annotations
from typing import Callable, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from conflict_interface.replay.replay_patch import Operation

from conflict_interface.logger_config import get_logger

logger = get_logger()


class ChangeType(Enum):
    """Types of changes that can trigger hooks."""
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"


@dataclass
class HookRegistration:
    """Represents a registered hook with its pattern and callback."""
    pattern: list[str]  # Path pattern with potential wildcards
    callback: Callable
    change_types: set[ChangeType]  # Which change types trigger this hook

    def matches(self, path: list[str], change_type: ChangeType) -> bool:
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

        return self._match_pattern(self.pattern, path)

    def _match_pattern(self, pattern: list[str], path: list[str]) -> bool:
        """
        Recursively match pattern against path.

        Args:
            pattern: Pattern elements to match
            path: Path elements to match against

        Returns:
            True if pattern matches path
        """
        # Base case: both empty means match
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
    path: list[str]
    old_value: Any
    new_value: Any


class HookSystem:
    """
    Manages hook registrations and queuing for GameObject changes.
    
    The hook system allows registration of callbacks that are triggered when
    specific paths in the game state are modified. It supports wildcard patterns
    for flexible matching.
    """
    
    def __init__(self):
        """Initialize the hook system."""
        self.hooks: list[HookRegistration] = []
        self.queued_hooks: list[QueuedHook] = []
        
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
            
        pattern = path_pattern.split(".")
        hook = HookRegistration(pattern, callback, change_types)
        self.hooks.append(hook)
        logger.debug(f"Registered hook for pattern: {path_pattern}")
        
    def queue_hook_from_operation(
        self, 
        operation: Operation,
        old_value: Any = None
    ) -> None:
        """
        Queue hooks based on a replay operation.
        
        Args:
            operation: The replay operation that occurred
            old_value: The old value before the operation (for replace operations)
        """
        from conflict_interface.replay.replay_patch import AddOperation, RemoveOperation, ReplaceOperation
        
        # Determine change type
        if isinstance(operation, AddOperation):
            change_type = ChangeType.ADD
            new_value = operation.new_value
        elif isinstance(operation, RemoveOperation):
            change_type = ChangeType.REMOVE
            new_value = None
        elif isinstance(operation, ReplaceOperation):
            change_type = ChangeType.REPLACE
            new_value = operation.new_value
        else:
            logger.warning(f"Unknown operation type: {type(operation)}")
            return
            
        path = operation.path
        # Find matching hooks
        for hook in self.hooks:
            if hook.matches(path, change_type):
                queued = QueuedHook(
                    callback=hook.callback,
                    change_type=change_type,
                    path=path,
                    old_value=old_value,
                    new_value=new_value
                )
                self.queued_hooks.append(queued)

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
