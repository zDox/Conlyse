from copy import deepcopy
from logging import getLogger
from typing import Any

from conflict_interface.hook_system.replay_hook import ReplayHook
from conflict_interface.hook_system.replay_hook_queue_element import ReplayHookQueueElement
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.replay.path_tree import PathTree

logger = getLogger()

class ReplayHookSystem:
    def __init__(self):
        self.hooks: dict[int, ReplayHook] = {} # Listening to Path -> Hook
        self.queued: dict[int, list[ReplayHookQueueElement]] = {}
        self.events: list[ReplayHookQueueElement] = []

    def register(self, replay_hook: ReplayHook):
        self.hooks[replay_hook.path] = replay_hook

    def deregister(self, hook_path: int):
        del self.hooks[hook_path]

    def unregister_all(self):
        self.hooks.clear()

    def que(self, hook_path: int, child_ref: Any, data: dict):
        assert hook_path in self.hooks
        hook = self.hooks[hook_path]
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

        new_queue_element = ReplayHookQueueElement(
            path= hook_path,
            reference = child_ref,
            changed_data = data
        )
        if hook.callback is None:
            self.events.append(new_queue_element)
        else:
            if self.queued.get(hook_path) is None:
                self.queued[hook_path] = [new_queue_element]
            else:
                self.queued[hook_path].append(new_queue_element)

    def get_events(self) -> list[ReplayHookQueueElement]:
        events = self.events
        self.events = []
        return events


    def get_old_values(self, changed_paths: list[int], tree: PathTree):
        # Here we use a trick.
        # By creating the smallest subtree that contains all paths from the root to each of the changed paths we get a list of nodes
        # that lie before / are parents to changed nodes. now if a hook points to any of these parents one of his children has been updated
        # therefore the hook needs to be queued given that the operation type fits
        steiner_tree = tree.build_steiner_tree(changed_paths)
        relevant_nodes = set(steiner_tree.keys())

        # intersect hook_paths and relevant_nodes to get the hooks to keep
        out = []
        for hook_path, hook in self.hooks.items():
            if hook_path not in relevant_nodes: continue

            for child in steiner_tree[hook_path]: # for prov in locations
                relevant_attribute_changed = False
                attribute_paths = steiner_tree.get(child) # attribute nodes of a prov
                if not attribute_paths: # no attributes found
                    logger.warning(f"Skipping hook {hook_path} as no attributes were found (Maby full province changed)")
                    continue

                changed_attributes = {}
                reference_to_child = None
                for attribute in attribute_paths: # for attribute node in attribute nodes of a prov
                    attribute_node = tree.idx_to_node[attribute] # actual node
                    reference_to_child = attribute_node.reference # ref to holder of attribute of prov aka a province
                    if not reference_to_child: # Important warning
                        logger.warning(f"Skipping Attribute {attribute_node.path_element} because the reference was not set")
                        continue

                    if attribute_node.path_element in hook.attributes: # if attribute name in listening hook attribures
                        old_ref = getattr(reference_to_child, attribute_node.path_element, None) # copy the attribute by acesssing the province
                        old_value = deepcopy(old_ref)
                        changed_attributes[attribute_node.path_element] = [old_value, None]
                        relevant_attribute_changed = True

                if not relevant_attribute_changed:
                    continue

                assert reference_to_child
                assert len(changed_attributes) > 0
                assert hook_path

                out.append((hook_path, reference_to_child, changed_attributes))

        return out

    def set_new_values(self, data, tree: PathTree):
        for hook_path, reference_to_child, changed_attributes in data:
            for attribute, value in changed_attributes.items():
                value[1] = getattr(reference_to_child, attribute, None)

        return data

    def execute_que(self):
        for path, que_elements in self.queued.items():
            hook = self.hooks[path]
            for ele in que_elements:
                try:
                    hook.callback(
                        ele.path,
                        ele.reference,
                        ele.changed_data
                    )
                except Exception as e:
                    logger.error(f"Error executing hook: {e}", exc_info=True)

        self.clear_que()

    def clear_que(self):
        self.queued = {}



