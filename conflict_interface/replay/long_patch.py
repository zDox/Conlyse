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


class HierOp:
    __slots__ = ("ops", "children", "leaf")

class Operation:
    __slots__ = ("op", "global_order", "value")

NO_VALUE = object()


def build_op_tree(patch_path: list[PatchGraphNode], path_tree: PathTree):
    root_op = HierOp.__new__(HierOp)
    root_op.ops = []
    root_op.children = {}
    root_op.leaf = True
    global_order_idx = 0

    for patch_node in patch_path:
        for op_type, path_idx, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
            # Get Full Path
            path_indices = path_tree.full_paths[path_idx]
            # Insert / Fold into Op Tree

            current = root_op
            for i, idx in enumerate(path_indices):
                if idx not in current.children:
                    if i == len(path_indices)-1:
                        # This path has never been changed before.
                        if len(current.ops) > 0 and current.ops[-1].op == REPLACE_OPERATION:
                            apply_operation(op_type, value, current.ops[-1].value, path_tree.idx_to_node[path_idx].path_element)
                        else:
                            # Add a new node
                            leaf_node = HierOp.__new__(HierOp)
                            operation = Operation.__new__(Operation)
                            operation.op = op_type
                            operation.global_order = global_order_idx
                            operation.value = value
                            leaf_node.ops = [operation]
                            leaf_node.children = {}
                            leaf_node.leaf = True
                            current.children[idx] = leaf_node
                        break

                    else:
                        # Add new path
                        assert len(current.ops) == 0, "Invariant - Only Strutural Nodes after Structural nodes - Violated"
                        node_op = HierOp.__new__(HierOp)
                        node_op.ops = []
                        node_op.children = {}
                        node_op.leaf = False
                        current.leaf = False
                        current.children[idx] = node_op

                else:
                    if i == len(path_indices)-1:
                        # This path was changed multiple times. Add an op
                        if len(current.ops) > 0 and current.ops[-1].op == REPLACE_OPERATION:
                            apply_operation(op_type, value, current.ops[-1].value, path_tree.idx_to_node[path_idx].path_element)
                        else:
                            operation = Operation.__new__(Operation)
                            operation.op = op_type
                            operation.global_order = global_order_idx
                            operation.value = value

                            current.children[idx].children = {}
                            current.children[idx].leaf = True

                            old_ops = current.children[idx].ops
                            if len(old_ops) == 0:
                                old_ops.append(operation)
                            else:
                                if old_ops[-1].op == REPLACE_OPERATION:
                                    assert op_type != ADD_OPERATION, "Invariant - Cant Add where there is already smth - Violated"
                                    old_ops[-1] = operation
                                else:
                                    old_ops.append(operation)

                        break

                current = current.children[idx]
            global_order_idx += 1

    return root_op

def collapse_op_tree(root: HierOp):
    op_types = []
    paths = []
    values = []
    global_orders = []

    stack = [(-1, root)]

    while stack:
        path, node = stack.pop()
        stack.extend(reversed(node.children.items()))

        for op in node.ops:
            op_types.append(op.op)
            paths.append(path)
            values.append(op.value)
            global_orders.append(op.global_order)

    combined = list(zip(global_orders, op_types, paths, values))

    # sort by global_orders (first element of each tuple)
    combined.sort(key=lambda x: x[0])

    # unzip back into separate arrays
    global_orders, op_types, paths, values = map(list, zip(*combined))
    return op_types, paths, values



OP_NAMES = {
    ADD_OPERATION: "ADD",
    REPLACE_OPERATION: "REPLACE",
    REMOVE_OPERATION: "REMOVE",
}

def print_op_tree(root: HierOp, path_tree: PathTree):
    stack = [(root, 0, None)]  # (node, depth, path_idx)

    while stack:
        node, depth, idx = stack.pop()

        indent = "  " * depth

        operation_str = ""
        for op in node.ops:
            operation_str += OP_NAMES.get(op.op, str(op.op)) + " "
        operation_str = operation_str[:-1]

        if not node.leaf:
            if idx is None:
                print(f"{indent}ROOT [{operation_str}]")
            else:
                print(f"{indent}{idx} [{operation_str}]")
            # push children in reverse order for natural printing
            for child_idx, child in reversed(node.children.items()):
                stack.append((child, depth + 1, child_idx))
        else:
            if len(node.ops) == 1:
                print(f"{indent}{idx} {path_tree.idx_to_node[int(idx)].path_element} [{operation_str}] = {str(node.ops[0].value)[:100]}")
            else:
                print(
                    f"{indent}{idx} {path_tree.idx_to_node[int(idx)].path_element} [{operation_str}] = {str(node.ops[0].value)[:30]}, {str(node.ops[1].value)[:30]}, ...")


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

    print_op_tree(op_tree, replay.storage.path_tree)

    build_time = t2 - t1
    print(f"Build Tree in {build_time * 1000} ms")
    print(f"Build ops / sec = {amount_ops_before / build_time}")


    collapsed = collapse_op_tree(op_tree)
    t3 = time.perf_counter()

    print_op_tree(op_tree, replay.storage.path_tree)

    amount_ops_after = len(collapsed[0])
    
    collapsed_time = t3 - t2
    
    print(f"Collapsed Tree in {collapsed_time * 1000} ms")
   
    print(f"Collapsed ops / sec = {amount_ops_before / collapsed_time}")
    print(f"Combined ops / sec = {amount_ops_before / ( collapsed_time + build_time)}")

    print(f"Ops before {amount_ops_before}, Ops After {amount_ops_after} Saved in %: {(amount_ops_before - amount_ops_after) / amount_ops_before * 100}%")


    # Test if it was actually correct
    ritf = ReplayInterface(TEST_DATA / "test_replay.bin", player_id=1, game_id=12345)
    ritf.open('r')
    ritf.jump_to(ritf.start_time)
    state_before = dump_any(ritf.game_state)
    ritf.jump_to_last_time()
    state_after_original = dump_any(ritf.game_state)
    ritf.jump_to(ritf.start_time)

    # build node
    long_patch_node = PatchGraphNode(int(ritf.start_time.timestamp()), int(ritf.last_time.timestamp()), *collapsed)
    ritf._apply_patches_and_update_state([long_patch_node], ritf.last_time)
    ritf.current_timestamp_index = bisect.bisect_left(ritf._time_stamps_cache, ritf.last_time)
    state_after_new = dump_any(ritf.game_state)

    compare_dicts(state_after_original, state_after_new)



