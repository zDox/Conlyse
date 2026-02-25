from __future__ import annotations

from logging import getLogger
from typing import Any
from typing import Callable
from typing import TYPE_CHECKING

from conflict_interface.hook_system.replay_hook import ReplayHook
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_queue_element import ReplayHookQueueElement
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION

if TYPE_CHECKING:
    from conflict_interface.replay.replaysegment import ReplaySegment

logger = getLogger()


class ReplayHookSystem:
    def __init__(self, replay):
        self._tags = set()  # Set of all registered hook tags
        self._hooks: dict[int, list[ReplayHook]] = {}  # Listening to Path -> list of Hooks
        self._hook_queue: dict[int, list[ReplayHookQueueElement]] = {}
        self._hook_events: list[ReplayHookEvent] = []
        self.replay: ReplaySegment = replay

    def register_hook(self, replay_hook: ReplayHook):
        if replay_hook.path in self._hooks:
            self._hooks[replay_hook.path].append(replay_hook)
        else:
            self._hooks[replay_hook.path] = [replay_hook]

    def unregister_hook(self, hook_path: int, callback: Callable | None):
        if hook_path not in self._hooks:
            return
        # Remove all hooks if callback equal to hook.callback
        removed_hooks = []
        for hook in self._hooks[hook_path]:
            if hook.callback == callback:
                removed_hooks.append(hook)
        self._hook_queue.pop(hook_path, None)
        for hook in removed_hooks:
            self._hooks[hook_path].remove(hook)

    def unregister_all_hooks(self):
        self._hooks.clear()

    def get_hooks(self):
        return self._hooks

    def que_hook_path(self, hook_path: int, child_ref: Any, data: dict):
        assert hook_path in self._hooks
        for hook in self._hooks[hook_path]:
            found = False
            for attribute, value in data.items():
                op_type = REPLACE_OPERATION
                if value[0] is None and value[1] is not None:
                    op_type = ADD_OPERATION
                if value[0] is not None and value[1] is None:
                    op_type = REMOVE_OPERATION
                if op_type in hook.change_types:
                    found = True

            if not found: return

            if hook.callback is None:
                self._hook_events.append(ReplayHookEvent(
                    tag=hook.tag,
                    reference=child_ref,
                    attributes=data
                ))
            else:
                new_queue_element = ReplayHookQueueElement(
                    path=hook_path,
                    reference=child_ref,
                    changed_data=data
                )
                if self._hook_queue.get(hook_path) is None:
                    self._hook_queue[hook_path] = [new_queue_element]
                else:
                    self._hook_queue[hook_path].append(new_queue_element)

    def execute_queue(self):
        for path, que_elements in self._hook_queue.items():
            for hook in self._hooks[path]:
                for ele in que_elements:
                    try:
                        hook.callback(
                            ele.reference,
                            ele.changed_data
                        )
                    except Exception as e:
                        logger.error(f"Error executing hook: {e}", exc_info=True)

        self.clear_queue()

    def clear_queue(self):
        self._hook_queue = {}

    """
    Event Trigger Registration/Unregistration Methods
    
    A single event trigger can be registered per path. 
    """

    def register_event_trigger(self, tag: ReplayHookTag, path: list[str], attributes: list[str] | None = None, search_start_depth: int = 0, search_end_depth: int = -1):
        """
        Registers an event trigger for a specific tag and path within the replay storage. The event
        trigger listens for specific change types (add, replace, or remove) at the specified path
        and associates them with the provided tag. If an event trigger with the same tag already
        exists, a ValueError is raised. If an event trigger already exists at the given path, it
        will be removed before registering the new one.

        Args:
            tag (ReplayHookTag): The unique identifier for the event trigger being registered.
            path (list[str]): A list of strings representing a path in the replay storage structure.
            attributes (list[str] | None): A list of attribute names to monitor for changes.
                Defaults to None. If None, all attributes are monitored.

        Raises:
            ValueError: If an event trigger with the same tag has already been registered.
        """
        if tag in self._tags:
            raise ValueError(f"Event trigger with tag '{tag}' is already registered.")
        self._tags.add(tag)
        path_idx = self.replay.storage.path_tree.path_list_to_idx(path)
        hook = ReplayHook(
            tag=tag,
            change_types=[ADD_OPERATION, REPLACE_OPERATION, REMOVE_OPERATION],
            attributes=attributes,
            path=path_idx,
            search_start_depth = search_start_depth,
            search_end_depth = search_end_depth
        )
        # Remove any existing event trigger at this path
        self.unregister_hook(path_idx, None)
        self.register_hook(hook)

    def unregister_event_trigger(self, path: list[str]) -> None:
        """Remove a previously registered event trigger."""

        path_idx = self.replay.storage.path_tree.path_list_to_idx(path)
        
        # Remove tag(s) from the set before unregistering the hook
        if path_idx in self._hooks:
            for hook in self._hooks[path_idx]:
                if hook.callback is None:  # Event triggers have callback=None
                    self._tags.discard(hook.tag)
        
        self.unregister_hook(path_idx, None)

    def poll_events(self) -> list[ReplayHookEvent]:
        """Retrieve and clear the queued events."""
        events = self._hook_events
        self._hook_events = []
        return events

    def add_segment_switch_event(self):
        self._hook_events.append(ReplayHookEvent(
            None, {}, ReplayHookTag.SegmentSwitch
        ))

