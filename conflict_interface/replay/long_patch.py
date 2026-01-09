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
    Build an operation tree indexed by path-tree node indices.

    This function walks the path tree (restricted to the Steiner tree `adj`)
    and accumulates all patch operations along `patch_path` into a single
    operation per path index.

    Multiple operations affecting the same path are merged according to
    semantic rules (e.g. REMOVE + ADD → REPLACE, ADD + REMOVE → NO-OP).
    Invalid operation sequences violate invariants and are assumed not
    to occur.

    Each stored operation is represented as a tuple:
        (op_type, path_index, value, time)

    where `time` is a monotonically increasing counter used to preserve
    relative ordering across merged operations.

    Args:
        patch_path: Ordered list of PatchGraphNode objects representing
            the patch sequence from source to target.
        adj: Adjacency list representing the Steiner subtree of the path tree
            containing all modified paths.
        root: Index of the root node in the path tree.

    Returns:
        A dictionary mapping path-tree node indices to their final merged
        operation tuple, or None if no operation applies.
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
            if old_value is None:
                idx_to_opnode[path] = (op_type, path, value, t)
                continue

            old_op_type = old_value[0]

            # REMOVE + ADD = REPLACE
            if old_value is not None and old_op_type == REMOVE_OPERATION and op_type == ADD_OPERATION:
                idx_to_opnode[path] = (REPLACE_OPERATION, path, value, t)

            # ADD + REMOVE = NO OP
            elif old_value is not None and old_op_type == ADD_OPERATION and op_type == REMOVE_OPERATION:
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

    for v in children:
        dfs_apply_ops(v, adj, get_child(v, value, path_tree), idx_to_opnode, path_tree)

    node_value = idx_to_opnode[u]
    if node_value is None: return

    node_time = node_value[3]

    for v in children:
        child_opnode = idx_to_opnode[v]
        child_op_type, _, child_value, child_time = child_opnode

        if child_opnode is None or child_time < node_time: continue

        apply_operation(child_op_type, child_value, value, path_tree.idx_to_node[v].path_element)


def get_child(v, value, path_tree: PathTree):
    """
    Retrieve the child value corresponding to a path-tree edge.

    Given a parent value and a child node index, this function extracts
    the appropriate sub-value based on the path element stored in
    the path tree.

    Supports both attribute-based access (for GameObject instances)
    and index/key-based access (for dicts or lists).

    Args:
        v: Path-tree node index of the child.
        value: Parent value.
        path_tree: PathTree containing path metadata.

    Returns:
        The child value corresponding to the path element.
    """
    idx = path_tree.idx_to_node[v].path_element
    if isinstance(value, GameObject):
        return getattr(value, idx)
    else:
        return value[idx]

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
    if from_time == to_time: return None
    shortest_path = patch_graph.find_patch_path(from_time, to_time)
    adj = create_adj_list(shortest_path, path_tree)
    op_tree = build_op_tree(shortest_path, adj, path_tree.root.index)
    operations = collapse_op_tree(op_tree, adj, path_tree)
    long_patch_node = PatchGraphNode(int(from_time.timestamp()), int(to_time.timestamp()), *operations)
    return long_patch_node

