import bisect
import time
from collections import deque
from datetime import timezone, datetime

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


class Node:
    __slots__ = ("value", "children")

def build_op_tree_v2(patch_path: list[PatchGraphNode], path_tree: PathTree):
    changed_paths = set()
    for patch_node in patch_path:
        changed_paths.update(patch_node.paths)

    op_tree = Node.__new__(Node)
    op_tree.children = {}
    op_tree.value = None
    idx_to_opnode = {path_tree.root.index: op_tree}

    adj = path_tree.build_steiner_tree(list(changed_paths))

    q = deque([(path_tree.root.index, op_tree)])
    pop = q.popleft
    add = q.append

    while q:
        u, parent = pop()

        for v in adj.get(u, []):
            new_node = Node.__new__(Node)
            new_node.children = {}
            new_node.value = None

            parent.children[v] = new_node
            idx_to_opnode[v] = new_node

            add((v, new_node))
    t = -1
    for patch_node in patch_path:
        for op_type, path, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
            t += 1
            old_value = idx_to_opnode[path].value
            idx_to_opnode[path].value = (op_type, path, value, t)
            # Reset values of all children
            q = deque([path])
            pop = q.popleft
            add = q.append

            while q:
                u = pop()

                for v in adj.get(u, []):
                    idx_to_opnode[v].value = None
                    add(v)

            # REMOVE + ADD = REPLACE
            if old_value is not None and old_value[0] == REMOVE_OPERATION and op_type == ADD_OPERATION:
                idx_to_opnode[path].value = (REPLACE_OPERATION, path, value, t)

            # ADD + REMOVE = NO OP
            if old_value is not None and old_value[0] == ADD_OPERATION and op_type == REMOVE_OPERATION:
                idx_to_opnode[path].value = None # If a newly added value gets removed then nothing happened

    op_types, paths, values = collapse_op_tree(idx_to_opnode, adj, path_tree)

    return op_types, paths, values

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

        node = idx_to_opnode[u]
        if node.value is not None:
            for v in adj.get(u, []):
                child_node = idx_to_opnode[v]
                if child_node.value is not None:
                    assert child_node.value[1] == v
                    apply_operation(child_node.value[0], child_node.value[2], node.value[2], path_tree.idx_to_node[v].path_element)

            op_types.append(node.value[0])
            paths.append(node.value[1])
            values.append(node.value[2])
            times.append(node.value[3])

        else:
            for v in adj.get(u, []):
                add(v)

    sorted_times, sorted_op_types, sorted_paths, sorted_values = zip(
        *sorted(zip(times, op_types, paths, values))
    )
    return list(sorted_op_types), list(sorted_paths), list(sorted_values)

if __name__ == "__main__":
    replay = Replay(TEST_DATA / "test_replay.bin", 'r')
    replay.open()
    target_time = datetime.fromtimestamp(replay.storage.patch_graph.time_stamps_cache[1000], tz= timezone.utc)
    patch_path = replay.storage.patch_graph.find_patch_path(replay.get_start_time(), target_time)
    game_state = replay.storage.initial_game_state
    amount_patches = len(patch_path)
    amount_ops_before = cost(patch_path)

    t1 = time.perf_counter()
    op_tree = build_op_tree_v2(patch_path, replay.storage.path_tree)
    t2 = time.perf_counter()

    build_time = t2 - t1
    print(f"Build Tree in {build_time * 1000} ms")
    print(f"Build ops / sec = {amount_ops_before / build_time}")

    t3 = time.perf_counter()

    amount_ops_after = len(op_tree[0])
    print(
        f"Ops before {amount_ops_before}, Ops After {amount_ops_after} Saved in %: {(amount_ops_before - amount_ops_after) / amount_ops_before * 100}%")

    # Test if it was actually correct
    ritf = ReplayInterface(TEST_DATA / "test_replay.bin", player_id=1, game_id=12345)
    ritf.open('r')
    ritf.jump_to(ritf.start_time)
    state_before = dump_any(ritf.game_state)
    tn1 = time.perf_counter()
    ritf.jump_to(target_time)
    tn2 = time.perf_counter()
    default_jump_time = tn2 - tn1
    print(f"Default jump time {(default_jump_time)*1000} ms")
    state_after_original = dump_any(ritf.game_state)
    ritf.jump_to(ritf.start_time)

    # build node
    t4 = time.perf_counter()
    long_patch_node = PatchGraphNode(int(ritf.start_time.timestamp()), int(target_time.timestamp()), *op_tree)
    ritf._apply_patches_and_update_state([long_patch_node], target_time)
    ritf.current_timestamp_index = bisect.bisect_left(ritf._time_stamps_cache, target_time)
    t5 = time.perf_counter()

    total_jump_time = t5 - t4 + build_time
    print(f"Total jump time: {total_jump_time * 1000} ms")
    print(f"Total ops / sec: " + str(amount_ops_before / total_jump_time))
    print(f"Speedup: {default_jump_time / total_jump_time}")

    state_after_new = dump_any(ritf.game_state)

    compare_dicts(state_after_original, state_after_new)