from __future__ import annotations

from logging import getLogger
from typing import Any
from typing import Callable
from typing import TYPE_CHECKING

from conflict_interface.data_types.map_state.province import Province
from conflict_interface.hook_system.replay_hook import ReplayHook
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_queue_element import ReplayHookQueueElement
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION

if TYPE_CHECKING:
    from conflict_interface.replay.replay import Replay

logger = getLogger()


class ReplayHookSystem:
    def __init__(self, replay):
        self._tags = set()  # Set of all registered hook tags
        self._hooks: dict[int, list[ReplayHook]] = {}  # Listening to Path -> list of Hooks
        self._hook_queue: dict[int, list[ReplayHookQueueElement]] = {}
        self._hook_events: list[ReplayHookEvent] = []
        self.replay: Replay = replay

    def _register_hook(self, replay_hook: ReplayHook):
        if replay_hook.path in self._hooks:
            self._hooks[replay_hook.path].append(replay_hook)
        else:
            self._hooks[replay_hook.path] = [replay_hook]

    def _unregister_hook(self, hook_path: int, callback: Callable | None):
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

    def register_event_trigger(self, tag: str, path: list[str], attributes: list[str]):
        """
        Register an event trigger for a specific path and attributes.

        The event trigger will queue events when the specified attributes
        at the given path change.

        Args:
        """
        if tag in self._tags:
            raise ValueError(f"Event trigger with tag '{tag}' is already registered.")
        self._tags.add(tag)
        path_idx = self.replay.storage.path_tree.path_list_to_idx(path)

        hook = ReplayHook(
            tag=tag,
            change_types=[ADD_OPERATION, REPLACE_OPERATION, REMOVE_OPERATION],
            attributes=attributes,
            path=path_idx
        )
        # Remove any existing event trigger at this path
        self._unregister_hook(path_idx, None)
        self._register_hook(hook)

    def unregister_event_trigger(self, path: list[str]) -> None:
        """Remove a previously registered event trigger."""

        path_idx = self.replay.storage.path_tree.path_list_to_idx(path)
        self._unregister_hook(path_idx, None)

    def poll_events(self) -> list[ReplayHookEvent]:
        """Retrieve and clear the queued events."""
        events = self._hook_events
        self._hook_events = []
        return events

    """
    Callback Registration/Unregistration Methods
    """

    def on_province_attribute_change(self, callback: Callable[[Province, dict], None], attributes: list[str]) -> None:
        """
        Register a callback for when an attribute of a province changes.

        The callback will be called with the province object:
        callback(province, changed_attributes)
        where province is the Province object of which at least one of
        the specified attributes has changed, and changed_attributes is a dict
        mapping attribute names to a tuple of (old_value, new_value).

        Args:
            callback: Function to call when the province attribute changes
            attributes: The name of the attributes to watch (e.g., "[owner_id", "resource_production"]).
        """
        path = ["states", "map_state", "map", "locations"]
        path_idx = self.replay.storage.path_tree.path_list_to_idx(path)

        hook = ReplayHook(
            tag="province_attribute_change",
            callback=callback,
            change_types=[ADD_OPERATION, REPLACE_OPERATION, REMOVE_OPERATION],
            attributes=attributes,
            path=path_idx
        )
        self._register_hook(hook)

    def remove_province_attribute_change_hook(self, callback: Callable[[Province, dict], None]) -> None:
        """Remove a previously registered province attribute change hook."""

        path = ["states", "map_state", "map", "locations"]
        path_idx = self.replay.storage.path_tree.path_list_to_idx(path)
        self._unregister_hook(path_idx, callback)
