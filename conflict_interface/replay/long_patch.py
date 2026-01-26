import time
from collections import deque
from datetime import datetime

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.op_tree_cpp import build_op_tree_fast
from conflict_interface.replay.apply_replay_helper import apply_operation
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree


def collapse_op_tree(idx_to_opnode: dict, adj, path_tree: PathTree):
    """
    Collapse an operation tree into a linearized patch representation.

    This function traverses the path tree and extracts all effective
    operations, applying parent operations to children where necessary
    to preserve correctness (e.g. replacing a parent object must update
    descendant operations).

    NO-OP entries are discarded. Remaining operations are sorted by
    their original time index to maintain causal ordering.

    Args:
        idx_to_opnode: Mapping from path-tree node indices to operation
            tuples produced by `build_op_tree`.
        adj: Adjacency list of the Steiner subtree.
        path_tree: The PathTree describing path hierarchy and structure.

    Returns:
        A tuple of three lists:
            - op_types: List of operation types
            - paths: Corresponding list of path indices
            - values: Corresponding list of operation values
        ordered by original operation time.
    """
    paths = []
    op_types = []
    values = []
    creation_times = []

    q = deque([path_tree.root.index])
    pop = q.popleft
    add = q.append

    while q:
        u = pop()

        op_node = idx_to_opnode[u]
        if op_node is not None:
            op_type, path, value, creation_time, last_change_time = op_node
            if op_type == -1: continue # NO OP -> Disregard

            dfs_apply_ops(u, adj, value, idx_to_opnode, path_tree)

            op_types.append(op_type)
            paths.append(path)
            values.append(value)
            creation_times.append(creation_time)

        else:
            for v in adj.get(u, []):
                add(v)

    sorted_times, sorted_op_types, sorted_paths, sorted_values = zip(
        *sorted(zip(creation_times, op_types, paths, values))
    )
    return list(sorted_op_types), list(sorted_paths), list(sorted_values)


def dfs_apply_ops(u, adj, value, idx_to_opnode, path_tree):
    """
    Propagate a parent operation's value down the path tree.

    When an operation applies to a parent path, its effects may need
    to be applied to child operations that occur later in time.
    This function performs a depth-first traversal to update
    descendant operations accordingly.

    Operations on children that occurred before the parent operation
    are left untouched.

    Args:
        u: Current path-tree node index.
        adj: Adjacency list of the path tree.
        value: The value associated with the parent operation.
        idx_to_opnode: Mapping of path indices to operation tuples.
        path_tree: PathTree used to resolve path elements and hierarchy.
    """
    children = adj.get(u, [])
    if not children: return
    if value is None: return


    node_value = idx_to_opnode[u]
    if node_value is None: return

    node_last_changed_time = node_value[4]

    pruned_children = []
    for v in children:
        child_opnode = idx_to_opnode[v]
        if child_opnode is None: continue
        child_op_type, _, child_value, child_creation_time, child_last_changed_time = child_opnode

        if child_last_changed_time < node_last_changed_time: continue
        pruned_children.append((child_creation_time, child_op_type, child_value, v))

    pruned_children.sort(key=lambda t: t[0])
    for _, child_op_type, child_value, v in pruned_children:
        path_element = path_tree.idx_to_node[v].path_element
        apply_operation(child_op_type, child_value, value, path_element)
        if child_op_type == -1 or child_op_type == REMOVE_OPERATION: continue # Noops and removed objects are nonexistent and therefore have no changes to be applied

        dfs_apply_ops(v, adj, get_child(value, path_element), idx_to_opnode, path_tree)


def get_child(value, path_element: int | str):
    """
    Retrieve the child value corresponding to a path-tree edge.

    Given a parent value and a child node index, this function extracts
    the appropriate sub-value based on the path element stored in
    the path tree.

    Supports both attribute-based access (for GameObject instances)
    and index/key-based access (for dicts or lists).

    Args:
        value:
        path_element:

    Returns:
        The child value corresponding to the path element.
    """
    if isinstance(value, GameObject):
        return getattr(value, path_element)
    else:
        return value[path_element]

def create_adj_list(patch_path: list[PatchGraphNode], path_tree: PathTree):
    """
    Construct the Steiner subtree adjacency list for modified paths.

    This function collects all paths modified by the patch sequence
    and builds the minimal subtree of the path tree that connects them.
    This limits subsequent traversals to only relevant nodes.

    Args:
        patch_path: List of PatchGraphNode objects whose operations
            define the modified paths.
        path_tree: The full PathTree.

    Returns:
        An adjacency list representing the Steiner subtree containing
        all changed paths.
    """

    changed_paths = set()
    for patch_node in patch_path:
        changed_paths.update(patch_node.paths)


    adj = path_tree.build_steiner_tree(list(changed_paths))

    return adj

def build_op_tree(patch_path: list[PatchGraphNode], adj, root):
    """Original docstring..."""
    # Pass PatchGraphNode data as nested lists (minimal overhead)
    ops_per_patch = []
    paths_per_patch = []

    for patch_node in patch_path:
        ops_per_patch.append(patch_node.op_types)
        paths_per_patch.append(patch_node.paths)

    # C++ returns: dict[int, tuple[int, int, int, int, int] | None]
    # where tuple is (op_type, path, value_idx_in_patch, creation_time, last_changed_time)
    t1 = time.perf_counter()
    result = build_op_tree_fast(ops_per_patch, paths_per_patch, adj, root)
    t2 = time.perf_counter()
    print((t2-t1)*1000)
    # Only reconstruct values for non-None entries
    idx_to_opnode = {}
    for path_idx, op_data in result.items():
        if op_data is None:
            idx_to_opnode[path_idx] = None
        elif op_data[0] == -1:  # NO-OP
            idx_to_opnode[path_idx] = op_data
        else:
            # Unpack: (op_type, path, value_composite, creation_time, last_changed_time)
            # value_composite encodes: (patch_idx << 32) | value_idx_in_patch
            op_type, path, value_composite, creation_time, last_changed_time = op_data
            patch_idx = value_composite >> 32
            value_idx = value_composite & 0xFFFFFFFF

            actual_value = patch_path[patch_idx].values[value_idx]
            idx_to_opnode[path_idx] = (op_type, path, actual_value, creation_time, last_changed_time)

    return idx_to_opnode


def create_long_patch(from_time: datetime, to_time: datetime, patch_graph: PatchGraph, path_tree: PathTree) -> PatchGraphNode | None:
    """
    Create a single consolidated patch spanning a time interval.

    This function finds the shortest patch path between two timestamps,
    merges all intermediate patches into a single equivalent patch,
    and collapses redundant operations while preserving semantics.

    The resulting PatchGraphNode represents the net effect of all
    changes between `from_time` and `to_time`.

    Args:
        from_time: Start time of the interval.
        to_time: End time of the interval.
        patch_graph: PatchGraph containing temporal patch relationships.
        path_tree: PathTree describing path hierarchy.

    Returns:
        A PatchGraphNode representing the consolidated patch over
        the given time range.
    """
    shortest_path = patch_graph.find_patch_path(from_time, to_time)
    adj = create_adj_list(shortest_path, path_tree)
    op_tree = build_op_tree(shortest_path, adj, path_tree.root.index)
    operations = collapse_op_tree(op_tree, adj, path_tree)
    long_patch_node = PatchGraphNode(int(from_time.timestamp()), int(to_time.timestamp()), *operations)

    return long_patch_node


