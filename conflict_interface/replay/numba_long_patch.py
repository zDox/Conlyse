from conflict_interface.replay.patch_graph_node import PatchGraphNode


def build_op_tree_2(patch_path: list[PatchGraphNode], adj, root):
    """Original docstring..."""
    from conflict_interface.op_tree_cpp import build_op_tree_fast

    # Pass PatchGraphNode data as nested lists (minimal overhead)
    ops_per_patch = []
    paths_per_patch = []

    for patch_node in patch_path:
        ops_per_patch.append(patch_node.op_types)
        paths_per_patch.append(patch_node.paths)

    # C++ returns: dict[int, tuple[int, int, int, int, int] | None]
    # where tuple is (op_type, path, value_idx_in_patch, creation_time, last_changed_time)
    result = build_op_tree_fast(ops_per_patch, paths_per_patch, adj, root)

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