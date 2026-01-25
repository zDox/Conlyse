# conflict_interface/steiner_tree_cpp.pyi
import numpy as np
from numpy.typing import NDArray

def build_steiner_tree(
    parent: NDArray[np.int_],
    tin: NDArray[np.int_],
    tout: NDArray[np.int_],
    root_idx: int,
    nodes: list[int],
    euler: NDArray[np.int_],
    depth: NDArray[np.int_],
    st: NDArray[np.int_],  # 2D array
    log_table: NDArray[np.int_],
    first: NDArray[np.int_]
) -> dict[int, list[int]]:
    """Build a Steiner tree from nodes using C++ implementation."""
    ...