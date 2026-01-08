import time
from collections import deque
from datetime import datetime

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.replay.apply_replay_helper import apply_operation
from conflict_interface.replay.constants import REPLACE_OPERATION, REMOVE_OPERATION, ADD_OPERATION
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree


def build_op_tree(patch_path: list[PatchGraphNode], adj, root):
    """
    This is the function you want to optimize.
    Edit this, save, run the script, and immediately see timing results.
    """

    idx_to_opnode = {}
    q = deque([root])
    pop = q.popleft

    while q:
        u = pop()
        idx_to_opnode[u] = None
        children = adj.get(u, ())
        if children:
            q.extend(children)

    t = -1
    for patch_node in patch_path:
        for op_type, path, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
            t += 1
            old_value = idx_to_opnode[path]

            # REMOVE + ADD = REPLACE
            if old_value is not None and old_value[0] == REMOVE_OPERATION and op_type == ADD_OPERATION:
                idx_to_opnode[path] = (REPLACE_OPERATION, path, value, t)

            # ADD + REMOVE = NO OP
            elif old_value is not None and old_value[0] == ADD_OPERATION and op_type == REMOVE_OPERATION:
                idx_to_opnode[path] = (-1, -1, -1, t)  # If a newly added value gets removed then nothing happened

            # All other cases
            else:
                idx_to_opnode[path] = (op_type, path, value, t)


            # NONE + ADD -> ADD
            # NONE + REPLACE -> REPLACE
            # NONE + REMOVE -> REMOVE
            # NO OP + ADD -> ADD
            # NO OP + REPLACE -> REPLACE
            # NO OP + REMOVE -> REMOVE
            # REMOVE + ADD -> REPLACE
            # REMOVE + REPLACE -> Error: Invariant Violated. You cannot replace a value that is not there
            # REMOVE + REMOVE -> Error: Invariant Violated. You cannot remove a value that is not there
            # ADD + REMOVE = NO OP
            # ADD + REPLACE = REPLACE; Technically this is an ADD. But since we cannot guarantee that the element is still the last in the list this would violate the "only add to end of list variant" therefore we handle it as a replace
            # ADD + ADD -> Error: Invariant Violated. You cannot add a value if there is already a value present
            # REPLACE + ADD -> Error: Invariant Violated. You cannot add a value if there is already a value present
            # REPLACE + REMOVE -> REMOVE
            # REPLACE + REPLACE -> REPLACE

    return idx_to_opnode


def collapse_op_tree(idx_to_opnode: dict, adj, path_tree: PathTree):
    paths = []
    op_types = []
    values = []
    times = []

    q = deque([path_tree.root.index])
    pop = q.popleft
    add = q.append

    while q:
        u = pop()

        op_node = idx_to_opnode[u]
        if op_node is not None:
            op_type, path, value, time = op_node
            if op_type == -1: continue # NO OP -> Disregard

            dfs_apply_ops(u, adj, value, idx_to_opnode, path_tree)

            op_types.append(op_type)
            paths.append(path)
            values.append(value)
            times.append(time)

        else:
            for v in adj.get(u, []):
                add(v)

    sorted_times, sorted_op_types, sorted_paths, sorted_values = zip(
        *sorted(zip(times, op_types, paths, values))
    )
    return list(sorted_op_types), list(sorted_paths), list(sorted_values)


def dfs_apply_ops(u, adj, value, idx_to_opnode, path_tree):
    children = adj.get(u, [])
    if not children: return
    if value is None: return

    for v in children:
        dfs_apply_ops(v, adj, get_child(v, value, path_tree), idx_to_opnode, path_tree)

    node_value = idx_to_opnode[u]
    if node_value is None: return

    node_time = node_value[3]

    for v in children:
        child_value = idx_to_opnode[v]

        if child_value is None or child_value[3] < node_time: continue

        apply_operation(child_value[0], child_value[2], value, path_tree.idx_to_node[v].path_element)


def get_child(v, value, path_tree: PathTree):
    idx = path_tree.idx_to_node[v].path_element
    if isinstance(value, GameObject):
        return getattr(value, idx)
    else:
        return value[idx]

def create_adj_list(patch_path: list[PatchGraphNode], path_tree: PathTree):
    changed_paths = set()
    for patch_node in patch_path:
        changed_paths.update(patch_node.paths)

    adj = path_tree.build_steiner_tree(list(changed_paths))
    return adj

def create_long_patch(from_time: datetime, to_time: datetime, patch_graph: PatchGraph, path_tree: PathTree) -> PatchGraphNode:
    shortest_path = patch_graph.find_patch_path(from_time, to_time)
    adj = create_adj_list(shortest_path, path_tree)
    op_tree = build_op_tree(shortest_path, adj, path_tree.root.index)
    operations = collapse_op_tree(op_tree, adj, path_tree)
    long_patch_node = PatchGraphNode(int(from_time.timestamp()), int(to_time.timestamp()), *operations)
    return long_patch_node

