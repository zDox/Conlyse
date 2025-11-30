import pickle
from typing import Any

import msgpack
import numpy as np

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.replay.path_tree import PathTree
from conflict_interface.replay.path_tree_node import PathTreeNode
from conflict_interface.utils.binary import BinaryWriter
from examples.value_analysis import is_primitive


class PatchGraphNode:
    def __init__(self, from_timestamp: int, to_timestamp: int, op_types: list[int], paths: list[int], values: list[Any], cost = None):
        self.from_timestamp = from_timestamp # Seconds since epoch
        self.to_timestamp = to_timestamp # Seconds since epoch
        self.op_types = op_types
        self.paths = paths
        self.values = values
        if not cost:
            self.cost = self.compute_cost()
        else:
            self.cost = cost

    def compute_cost(self) -> int:
        """Compute the cost of this patch node."""
        return len(self.op_types)

    def serialize(self, new_path_nodes: list[PathTreeNode]) -> memoryview:
        writer = BinaryWriter()

        # Header
        writer.write_int64(self.from_timestamp)
        writer.write_int64(self.to_timestamp)
        writer.write_int32(self.cost)
        writer.write_uint32(len(self.op_types))
        writer.write_uint32(len(new_path_nodes))

        # Path Nodes
        for node in new_path_nodes:
            writer.write_bytes(node.serialize())

        # Optypes, paths
        writer.write_bytes(np.array(self.op_types, dtype=np.int8).tobytes())
        writer.write_bytes(np.array(self.paths, dtype=np.uint32).tobytes())

        # values
        value_types = []
        primitives = []
        complexes = []

        for v in self.values:
            if is_primitive(v):
                value_types.append(0)
                primitives.append(v)
            else:
                value_types.append(1)
                GameObject.set_game_recursive(v, None)
                complexes.append(v)

        writer.write_uint32(len(value_types))
        writer.write_bytes(np.array(value_types, dtype=np.int8).tobytes())

        primitive_blob = msgpack.packb(primitives)
        writer.write_uint32(len(primitive_blob))
        writer.write_bytes(primitive_blob)

        complex_blob = pickle.dumps(complexes, protocol=pickle.HIGHEST_PROTOCOL)
        writer.write_uint32(len(complex_blob))
        writer.write_bytes(complex_blob)
        return writer.getbuffer()

    def deserialize(self, data: bytes) -> 'PatchGraphNode':
        pass
