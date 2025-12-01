import pickle
import struct
from typing import Any

import msgpack
import numpy as np

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.utils.binary import BinaryReader
from conflict_interface.utils.binary import BinaryWriter
from conflict_interface.utils.helper import is_primitive


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

    def serialize(self, new_paths: list[list[str | int]]) -> memoryview:
        writer = BinaryWriter()

        # Header
        writer.write_int64(self.from_timestamp)
        writer.write_int64(self.to_timestamp)
        writer.write_int32(self.cost)
        writer.write_uint32(len(self.op_types))

        # Original Paths
        new_paths_blob = msgpack.packb(new_paths)
        writer.write_uint32(len(new_paths_blob))
        writer.write_bytes(new_paths_blob)

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

        writer.write_bytes(np.array(value_types, dtype=np.int8).tobytes())

        primitive_blob = msgpack.packb(primitives)
        writer.write_uint32(len(primitive_blob))
        writer.write_bytes(primitive_blob)

        complex_blob = pickle.dumps(complexes, protocol=pickle.HIGHEST_PROTOCOL)
        writer.write_uint32(len(complex_blob))
        writer.write_bytes(complex_blob)
        return writer.getbuffer()

    @staticmethod
    def deserialize(patch_b) -> tuple['PatchGraphNode', list[list[str | int]]]:
        reader = BinaryReader(patch_b)

        from_ts = reader.read_int64()
        to_ts = reader.read_int64()
        cost = reader.read_int32()

        num_operations = reader.read_uint32()

        len_new_paths = reader.read_uint32()
        new_paths = msgpack.unpackb(reader.read_bytes_view(len_new_paths), raw=False)

        op_types = np.frombuffer(reader.read_bytes(num_operations), dtype=np.int8)
        paths = np.frombuffer(reader.read_bytes_view(num_operations * 4), dtype=np.int32)

        value_types = reader.read_bytes_view(num_operations)

        len_primitives = reader.read_uint32()
        primitives = reader.read_bytes_view(len_primitives)

        len_complexes = reader.read_uint32()
        complexes = reader.read_bytes_view(len_complexes)

        primitive_values = msgpack.unpackb(primitives, raw=False)
        complex_values = pickle.loads(complexes)

        values = []
        prim_idx = 0
        complex_idx = 0
        for type_ in value_types:
            if type_ == 0:
                values.append(primitive_values[prim_idx])
                prim_idx += 1
            else:
                values.append(complex_values[complex_idx])
                complex_idx += 1

        patch_graph_node = PatchGraphNode(
            from_timestamp=from_ts,
            to_timestamp=to_ts,
            op_types=op_types.tolist(),
            paths=paths.tolist(),
            values=values,
            cost=cost
        )
        return patch_graph_node, new_paths

    @staticmethod
    def extract_tree_nodes(patch_b) -> list[list[str | int]]:
        offset = 24  # 8 + 8 + 4 + 4

        # Read uint32 (use '<I' for little-endian unsigned int, '>I' for big-endian)
        new_paths_len = struct.unpack_from('<I', patch_b, offset)[0]
        offset += 4

        new_paths_blob = patch_b[offset:offset + new_paths_len]
        return msgpack.unpackb(new_paths_blob, raw=False)
