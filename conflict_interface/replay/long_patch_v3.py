import bisect
import time
from collections import deque
from datetime import timezone, datetime

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_json import dump_any
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.apply_replay_helper import apply_operation
from conflict_interface.replay.constants import ADD_OPERATION, REMOVE_OPERATION, REPLACE_OPERATION
from conflict_interface.replay.long_patch_v2 import cost
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree
from conflict_interface.replay.replay import Replay
from paths import TEST_DATA
from tests.helper_functions import compare_dicts


# ============================================================================
# EDIT THIS FUNCTION TO TEST YOUR OPTIMIZATIONS
# ============================================================================
def build_op_tree_v2(patch_path: list[PatchGraphNode], path_tree: PathTree):
    """
    This is the function you want to optimize.
    Edit this, save, run the script, and immediately see timing results.
    """
    changed_paths = set()
    for patch_node in patch_path:
        changed_paths.update(patch_node.paths)

    idx_to_opnode = {}

    adj = path_tree.build_steiner_tree(list(changed_paths))

    q = deque([path_tree.root.index])
    pop = q.popleft
    add = q.append

    while q:
        u = pop()
        idx_to_opnode[u] = None
        for v in adj.get(u, []):
            add(v)

    t = -1
    for patch_node in patch_path:
        for op_type, path, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
            t += 1
            old_value = idx_to_opnode[path]
            idx_to_opnode[path] = (op_type, path, value, t)

            # REMOVE + ADD = REPLACE
            if old_value is not None and old_value[0] == REMOVE_OPERATION and op_type == ADD_OPERATION:
                idx_to_opnode[path] = (REPLACE_OPERATION, path, value, t)

            # ADD + REMOVE = NO OP
            if old_value is not None and old_value[0] == ADD_OPERATION and op_type == REMOVE_OPERATION:
                idx_to_opnode[path] = (-1, -1, -1, t)  # If a newly added value gets removed then nothing happened

    op_types, paths, values = collapse_op_tree(idx_to_opnode, adj, path_tree)
    #print_op_tree(adj, idx_to_opnode, path_tree)

    return op_types, paths, values


# ============================================================================


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

        value = idx_to_opnode[u]
        if value is not None:
            if value[0] == -1: continue

            dfs_apply_ops(u, adj, value[2], idx_to_opnode, path_tree)

            op_types.append(value[0])
            paths.append(value[1])
            values.append(value[2])
            times.append(value[3])

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

    for v in children:
        dfs_apply_ops(v, adj, get_child(v, value, path_tree), idx_to_opnode, path_tree)

    node_value = idx_to_opnode[u]
    if node_value is None: return

    node_time = node_value[3]

    for v in children:
        child_value = idx_to_opnode[v]

        if child_value is None or child_value[3] < node_time: continue

        apply_operation(child_value[0], child_value[2], value, path_tree.idx_to_node[v].path_element)

def get_child(v, value, path_tree:PathTree):
    idx = path_tree.idx_to_node[v].path_element
    if isinstance(value, GameObject):
        return getattr(value, idx)
    else:
        return value[idx]


# ============================================================================
# SIMPLE BENCHMARK - Just run and see results
# ============================================================================
def quick_bench(target_idx=6000, runs=20):
    """Quick benchmark - just change code above and run this."""
    import gc

    replay = Replay(TEST_DATA / "test_replay.bin", 'r')
    replay.open()

    target_time = datetime.fromtimestamp(
        replay.storage.patch_graph.time_stamps_cache[target_idx],
        tz=timezone.utc
    )

    patch_path = replay.storage.patch_graph.find_patch_path(
        replay.get_start_time(),
        target_time
    )

    # Warmup
    _ = build_op_tree_v2(patch_path, replay.storage.path_tree)
    gc.collect()

    # Time it
    times = []
    for _ in range(runs):
        t1 = time.perf_counter()
        op_tree = build_op_tree_v2(patch_path, replay.storage.path_tree)
        t2 = time.perf_counter()
        times.append((t2 - t1) * 1000)
        gc.collect()

    min_time = min(times)
    avg_time = sum(times) / len(times)
    ops_before = cost(patch_path)
    ops_after = len(op_tree[0])

    print(f"Time: {min_time:.2f}ms (min) | {avg_time:.2f}ms (avg)")
    print(f"Ops:  {ops_before:,} → {ops_after:,} ({(ops_before - ops_after) / ops_before * 100:.1f}% saved)")
    print(f"Rate: {ops_before / min_time * 1000:,.0f} ops/sec")

    return min_time, op_tree

def print_op_tree(adj, idx_to_opnode, path_tree: PathTree):
    print("=" * 80)
    print(f"OPERATION TREE")
    print("=" * 80)

    op_names = {
        ADD_OPERATION: "ADD",
        REMOVE_OPERATION: "REMOVE",
        REPLACE_OPERATION: "REPLACE",
        -1: "NO OP",
    }
    stack = [(path_tree.root.index, 0)]  # (node, depth, path_idx)

    while stack:
        idx, depth = stack.pop()

        indent = "   " * depth
        value = idx_to_opnode[idx]
        if value is None:
            print(f"{indent}{idx}")
        else:
            if value[0] == -1:
                print(f"{indent}{idx} t: {value[3]} {op_names[value[0]]}")
            else:
                print(f"{indent}{idx} t: {value[3]} {op_names[value[0]]} {path_tree.idx_to_node[value[1]].path_element} = {str(value[2])[:100]} ")
        for child_idx in reversed(adj.get(idx, [])):
            stack.append((child_idx, depth + 1))



def verify(target_idx=6000):
    """Quick verification that results are correct."""
    replay = Replay(TEST_DATA / "test_replay.bin", 'r')
    replay.open()

    target_time = datetime.fromtimestamp(
        replay.storage.patch_graph.time_stamps_cache[target_idx],
        tz=timezone.utc
    )

    patch_path = replay.storage.patch_graph.find_patch_path(
        replay.get_start_time(),
        target_time
    )

    op_tree = build_op_tree_v2(patch_path, replay.storage.path_tree)

    # Get original state
    ritf = ReplayInterface(TEST_DATA / "test_replay.bin", player_id=1, game_id=12345)
    ritf.open('r')
    ritf.jump_to(ritf.start_time)
    ritf.jump_to(target_time)
    state_original = dump_any(ritf.game_state)

    # Get optimized state
    ritf.jump_to(ritf.start_time)
    t1 = time.perf_counter()
    long_patch_node = PatchGraphNode(
        int(ritf.start_time.timestamp()),
        int(target_time.timestamp()),
        *op_tree
    )
    ritf._apply_patches_and_update_state([long_patch_node], target_time)
    ritf.current_timestamp_index = bisect.bisect_left(ritf._time_stamps_cache, target_time)
    t2 = time.perf_counter()
    print(f"Additional Jump Time: {(t2 - t1)*1000}ms")
    state_optimized = dump_any(ritf.game_state)


    try:
        compare_dicts(state_original, state_optimized)
        print("✓ Correct")
        return True
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("QUICK BENCHMARK")
    print("=" * 60)
    quick_bench(target_idx=1000, runs=20)
    print()
    verify(target_idx=1000)
