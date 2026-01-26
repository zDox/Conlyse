# conflict_interface/replay/op_tree_cpp.pyi
def build_op_tree_fast(
        ops_per_patch: list[list[int]],
        paths_per_patch: list[list[int]],
        adj: dict[int, list[int]],
        root: int
) -> dict[int, tuple[int, int, int, int, int] | None]:
    """
    Fast C++ operation tree builder.

    Returns dict mapping path_idx to:
        - None if no operation
        - (op_type, path, value_composite, creation_time, last_changed_time)
          where value_composite = (patch_idx << 32) | value_idx_in_patch
    """
    ...