import bisect
import time

from conflict_interface.data_types.game_object_json import dump_any
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.apply_replay_helper import apply_operation
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree
from conflict_interface.replay.replay import Replay
from paths import TEST_DATA
from tests.helper_functions import compare_dicts

def build_op_tree(patch_path: list[PatchGraphNode], path_tree: PathTree):
    other_ops = []
    current_vals = {}
    global_order_idx = 0
    for patch_node in patch_path:
        for op_type, path_idx, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
            if op_type == REMOVE_OPERATION:
                other_ops.append((op_type, path_idx, value, global_order_idx))
                current_vals[path_idx] = (None, op_type, global_order_idx)
                global_order_idx += 1
                continue

            if op_type == ADD_OPERATION:
                other_ops.append((op_type, path_idx, value, global_order_idx))
                current_vals[path_idx] = (value, op_type, global_order_idx)

            else:
                current_vals[path_idx] = (value, op_type, global_order_idx)

            global_order_idx += 1

    replace_ops = []
    for path, (value, op_type, global_order_idx) in current_vals.items():
        if op_type == REPLACE_OPERATION:
            replace_ops.append((op_type, path, value, global_order_idx))

    operations = other_ops + replace_ops
    operations.sort(key=lambda x: x[3])
    return operations[:3]



OP_NAMES = {
    ADD_OPERATION: "ADD",
    REPLACE_OPERATION: "REPLACE",
    REMOVE_OPERATION: "REMOVE",
}


def cost(patch_path: list[PatchGraphNode]):
    return sum(x.cost for x in patch_path)


if __name__ == "__main__":
    replay = Replay(TEST_DATA / "test_replay.bin", 'r')
    replay.open()
    patch_path = replay.storage.patch_graph.find_patch_path(replay.get_start_time(), replay.get_last_time())
    amount_patches = len(patch_path)
    amount_ops_before = cost(patch_path)

    t1 = time.perf_counter()
    op_tree = build_op_tree(patch_path, replay.storage.path_tree)
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
    ritf.jump_to_last_time()
    state_after_original = dump_any(ritf.game_state)
    ritf.jump_to(ritf.start_time)

    # build node
    long_patch_node = PatchGraphNode(int(ritf.start_time.timestamp()), int(ritf.last_time.timestamp()), *op_tree)
    ritf._apply_patches_and_update_state([long_patch_node], ritf.last_time)
    ritf.current_timestamp_index = bisect.bisect_left(ritf._time_stamps_cache, ritf.last_time)
    state_after_new = dump_any(ritf.game_state)

    compare_dicts(state_after_original, state_after_new)



