from __future__ import annotations

import os
import pickle
import struct
from pathlib import Path
from typing import TYPE_CHECKING

import lz4.frame
import msgpack
import numpy as np

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.replay.metadata import Metadata
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface


class ReplayStorage:
    def __init__(self):
        self._metadata_b: bytes | None = None
        self._initial_game_state_b: bytes | None = None
        self._static_map_data_b: bytes | None = None
        self._path_tree_b: bytes | None = None
        self._patch_graph_b: bytes | None = None

        self.metadata: Metadata | None = None
        self.initial_game_state: GameState | None = None
        self.static_map_data: StaticMapData | None = None
        self.path_tree: PathTree | None = None
        self.patch_graph: PatchGraph | None = None

        self.compressor = lz4.frame.compress
        self.decompressor = lz4.frame.decompress

    def read_full_from_disk(self, file_path: Path):
        data = []
        with open(file_path, 'rb') as f:
            while True:
                length_bytes = f.read(4)
                if not length_bytes:
                    break

                (length, ) = struct.unpack('>I', length_bytes)
                compressed = f.read(length)
                decompressed = self.decompressor(compressed)
                data.append(decompressed)

        self._metadata_b = data[0]
        self._initial_game_state_b = data[1]
        self._static_map_data_b = data[2]
        self._path_tree_b = data[3]
        self._patch_graph_b = data[4]

    def write_full_to_disk(self, file_path: Path):
        print("Saving")
        assert self._metadata_b is not None, "Metadata is not recorded in the replay."
        assert self._initial_game_state_b is not None, "Initial game state is not recorded in the replay."
        assert self._static_map_data_b is not None, "Static map data is not recorded in the replay."
        assert self._path_tree_b is not None, "Path tree is not recorded in the replay."
        assert self._patch_graph_b is not None, "Patch graph is not recorded in the replay."
        data_chunks = [
            self._metadata_b,
            self._initial_game_state_b,
            self._static_map_data_b,
            self._path_tree_b,
            self._patch_graph_b
        ]

        # Partial compression for partial (metadata) reads.
        with open(file_path, 'wb') as f:
            for chunk in data_chunks:
                compressed = self.compressor(chunk)
                length = len(compressed)
                f.write(struct.pack('>I', length))
                f.write(compressed)

    def create_new_file(self, file_path: Path):
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def initialize(self):
        self.metadata = Metadata(
            start_time = 0,
            last_time = 0
        )
        self.path_tree = PathTree()
        self.patch_graph = PatchGraph()

    def load_metadata(self) -> Metadata:
        if self._metadata_b is None:
            raise ValueError("Metadata is not recorded in the replay.")
        self.metadata = pickle.loads(self._metadata_b)
        return self.metadata

    def load_initial_game_state(self, game: ReplayInterface) -> GameState:
        if self._initial_game_state_b is None:
            raise ValueError("Initial game state is not recorded in the replay.")

        self.initial_game_state =  pickle.loads(self._initial_game_state_b)
        GameObject.set_game_recursive(self.initial_game_state, game)
        return self.initial_game_state

    def load_static_map_data(self, game: ReplayInterface) -> StaticMapData:
        if self._static_map_data_b is None:
            raise ValueError("Static map data is not recorded in the replay.")
        self.static_map_data = pickle.loads(self._static_map_data_b)
        GameObject.set_game_recursive(self.static_map_data, game)
        return self.static_map_data

    def load_path_tree(self) -> PathTree:
        if self._path_tree_b is None:
            raise ValueError("Path tree is not recorded in the replay.")
        self.path_tree = pickle.loads(self._path_tree_b)
        return self.path_tree

    def load_patches(self, game: ReplayInterface) -> PatchGraph:
        if self._patch_graph_b is None:
            raise ValueError("Patch graph is not recorded in the replay.")

        data = self._patch_graph_b
        MAGIC = b"PGF1"

        # Validate magic number
        if data[:4] != MAGIC:
            raise ValueError("Invalid file format: magic number mismatch")

        # Read version
        version = struct.unpack("<I", data[4:8])[0]
        if version != 1:
            raise ValueError(f"Unsupported version: {version}")

        offset = 8
        layers = {}

        # Read all blocks
        while offset < len(data):
            block_id = struct.unpack("<B", data[offset:offset + 1])[0]
            block_size = struct.unpack("<Q", data[offset + 1:offset + 9])[0]
            offset += 9

            block_data = data[offset:offset + block_size]
            layers[block_id] = block_data
            offset += block_size

        # ------------------------------------------------------------------
        # LAYER 1 — skeleton (timestamps + edges)
        # ------------------------------------------------------------------
        layer1 = layers[1]
        pos = 0

        # Read timestamps
        num_timestamps = struct.unpack("<I", layer1[pos:pos + 4])[0]
        pos += 4
        time_stamps_array = np.frombuffer(
            layer1[pos:pos + num_timestamps * 8],
            dtype=np.int64
        )
        pos += num_timestamps * 8

        # Read edges
        num_edges = struct.unpack("<I", layer1[pos:pos + 4])[0]
        pos += 4
        edges = np.frombuffer(
            layer1[pos:pos + num_edges * 2 * 8],
            dtype=np.int64
        ).reshape((num_edges, 2))
        pos += num_edges * 2 * 8

        num_adj_concat = struct.unpack("<I", layer1[pos:pos + 4])[0]
        pos += 4
        adj_concat_arr = np.frombuffer(
            layer1[pos:pos + num_adj_concat * 8],
            dtype=np.int64
        )
        pos += num_adj_concat * 8

        num_adj_offsets = struct.unpack("<I", layer1[pos:pos + 4])[0]
        pos += 4
        adj_offsets_arr = np.frombuffer(
            layer1[pos:pos + num_adj_offsets * 4],
            dtype=np.int32
        )

        # ------------------------------------------------------------------
        # LAYER 2 — node meta (costs + op_types + paths + value_type_indicators)
        # ------------------------------------------------------------------
        layer2 = layers[2]
        pos = 0

        # Read costs
        num_costs = struct.unpack("<I", layer2[pos:pos + 4])[0]
        pos += 4
        costs = np.frombuffer(layer2[pos:pos + num_costs * 4], dtype=np.int32)
        pos += num_costs * 4

        # Read op_types
        num_op_types = struct.unpack("<I", layer2[pos:pos + 4])[0]
        pos += 4
        op_types_arr = np.frombuffer(layer2[pos:pos + num_op_types], dtype=np.int8)
        pos += num_op_types

        num_op_types_offsets = struct.unpack("<I", layer2[pos:pos + 4])[0]
        pos += 4
        op_types_offsets_arr = np.frombuffer(
            layer2[pos:pos + num_op_types_offsets * 4],
            dtype=np.int32
        )
        pos += num_op_types_offsets * 4

        # Read paths
        num_paths = struct.unpack("<I", layer2[pos:pos + 4])[0]
        pos += 4
        paths_arr = np.frombuffer(layer2[pos:pos + num_paths * 4], dtype=np.int32)
        pos += num_paths * 4

        num_paths_offsets = struct.unpack("<I", layer2[pos:pos + 4])[0]
        pos += 4
        paths_offsets_arr = np.frombuffer(
            layer2[pos:pos + num_paths_offsets * 4],
            dtype=np.int32
        )
        pos += num_paths_offsets * 4

        # Read value type indicators
        num_value_type_indicators = struct.unpack("<I", layer2[pos:pos + 4])[0]
        pos += 4
        value_type_indicators = np.frombuffer(
            layer2[pos:pos + num_value_type_indicators],
            dtype=np.int8
        )

        # ------------------------------------------------------------------
        # LAYER 3 — primitive values
        # ------------------------------------------------------------------
        layer3 = layers[3]
        pos = 0

        # Read primitive bytes
        num_primitive_bytes = struct.unpack("<I", layer3[pos:pos + 4])[0]
        pos += 4
        primitive_bytes = layer3[pos:pos + num_primitive_bytes]
        pos += num_primitive_bytes

        # Read primitive offsets
        num_primitive_offsets = struct.unpack("<I", layer3[pos:pos + 4])[0]
        pos += 4
        primitive_offsets_arr = np.frombuffer(
            layer3[pos:pos + num_primitive_offsets * 4],
            dtype=np.int32
        )
        pos += num_primitive_offsets * 4

        # Read primitive types
        num_primitive_types = struct.unpack("<I", layer3[pos:pos + 4])[0]
        pos += 4
        primitive_types_arr = np.frombuffer(
            layer3[pos:pos + num_primitive_types],
            dtype=np.int8
        )

        # ------------------------------------------------------------------
        # LAYER 4 — complex values
        # ------------------------------------------------------------------
        layer4 = layers[4]
        pos = 0

        # Read complex bytes
        num_complex_bytes = struct.unpack("<I", layer4[pos:pos + 4])[0]
        pos += 4
        complex_bytes = layer4[pos:pos + num_complex_bytes]
        pos += num_complex_bytes

        # Read complex offsets
        num_complex_offsets = struct.unpack("<I", layer4[pos:pos + 4])[0]
        pos += 4
        complex_offsets_arr = np.frombuffer(
            layer4[pos:pos + num_complex_offsets * 4],
            dtype=np.int32
        )

        # ------------------------------------------------------------------
        # RECONSTRUCT PATCH GRAPH
        # ------------------------------------------------------------------
        patch_graph = PatchGraph()
        patch_graph.time_stamps_cache = time_stamps_array.tolist()
        # Restore adjacency list

        for i, ts in enumerate(time_stamps_array):
            adj_start = adj_offsets_arr[i]
            adj_end = adj_offsets_arr[i + 1]
            neighbors = adj_concat_arr[adj_start:adj_end].tolist()
            patch_graph.adj[int(ts)] = neighbors


        # Indices to track position in primitive and complex arrays
        primitive_idx = 0
        complex_idx = 0
        value_indicator_idx = 0

        for i in range(num_edges):
            from_ts = int(edges[i, 0])
            to_ts = int(edges[i, 1])
            cost = int(costs[i])

            # Extract op_types for this patch
            op_types_start = op_types_offsets_arr[i]
            op_types_end = op_types_offsets_arr[i + 1]
            op_types = op_types_arr[op_types_start:op_types_end].tolist()

            # Extract paths for this patch
            paths_start = paths_offsets_arr[i]
            paths_end = paths_offsets_arr[i + 1]
            paths = paths_arr[paths_start:paths_end].tolist()

            # Reconstruct values using type indicators
            num_values = len(op_types)
            values = []

            for j in range(num_values):
                # Use the indicator to determine if this value is primitive (0) or complex (1)
                if value_type_indicators[value_indicator_idx] == 0:
                    # Primitive value - decode from msgpack
                    prim_start = primitive_offsets_arr[primitive_idx]
                    prim_end = primitive_offsets_arr[primitive_idx + 1]
                    prim_data = primitive_bytes[prim_start:prim_end]
                    value = msgpack.unpackb(prim_data, raw=False)
                    values.append(value)
                    primitive_idx += 1
                else:
                    # Complex value - decode from pickle
                    comp_start = complex_offsets_arr[complex_idx]
                    comp_end = complex_offsets_arr[complex_idx + 1]
                    comp_data = complex_bytes[comp_start:comp_end]
                    value = pickle.loads(comp_data)
                    GameObject.set_game_recursive(value, game)
                    values.append(value)
                    complex_idx += 1

                value_indicator_idx += 1

            # Create PatchGraphNode
            patch_node = PatchGraphNode(
                from_timestamp=from_ts,
                to_timestamp=to_ts,
                cost=cost,
                op_types=op_types,
                paths=paths,
                values=values
            )

            # Add to patch graph
            patch_graph.patches[(from_ts, to_ts)] = patch_node

        self.patch_graph = patch_graph
        return patch_graph

    def unload_metadata(self):
        self._metadata_b = pickle.dumps(self.metadata)

    def unload_initial_game_state(self, game_state: GameState):
        game = game_state.game
        GameObject.set_game_recursive(game_state, None)
        self._initial_game_state_b = pickle.dumps(game_state)
        GameObject.set_game_recursive(game_state, game)
        self.initial_game_state = game_state

    def unload_static_map_data(self, static_map_data: StaticMapData):
        game = static_map_data.game
        GameObject.set_game_recursive(static_map_data, None)
        self._static_map_data_b = pickle.dumps(static_map_data)
        GameObject.set_game_recursive(static_map_data, game)
        self.static_map_data = static_map_data

    def unload_path_tree(self):
        self._path_tree_b = pickle.dumps(self.path_tree)

    def unload_patches(self):
        MAGIC = b"PGF1"  # 4-byte magic number
        VERSION = 1  # file format version

        def encode_primitive(value):
            return msgpack.packb(value, use_bin_type=True)

        def encode_complex(value):
            GameObject.set_game_recursive(value, None)
            return pickle.dumps(value, protocol=5)

        def is_primitive(value):
            return isinstance(value, (int, float, bool, str, bytes))

        def is_primitive_container(value):
            if is_primitive(value):
                return True
            if isinstance(value, list):
                return all(is_primitive_container(x) for x in value)
            if isinstance(value, dict):
                return all(isinstance(k, str) and is_primitive_container(v) for k, v in value.items())
            return False

        patch_graph = self.patch_graph
        patches = list(patch_graph.patches.items())
        N = len(patches)

        # ------------------------------------------------------------------
        # LAYER 1 — skeleton (timestamps + edges)
        # ------------------------------------------------------------------
        time_stamps_array = np.array(sorted(patch_graph.time_stamps_cache), dtype=np.int64)

        edges = np.zeros((N, 2), dtype=np.int64)
        for i, ((f_ts, t_ts), _) in enumerate(patches):
            edges[i, 0] = f_ts
            edges[i, 1] = t_ts

        # Build adjacency list in a flat format
        # For each timestamp, store: [num_neighbors, neighbor1, neighbor2, ...]
        adj_concat = []
        adj_offsets = [0]

        for ts in time_stamps_array:
            neighbors = patch_graph.adj.get(int(ts), [])
            adj_concat.extend(neighbors)
            adj_offsets.append(len(adj_concat))

        adj_concat_arr = np.array(adj_concat, dtype=np.int64)
        adj_offsets_arr = np.array(adj_offsets, dtype=np.int32)

        layer1_payload = b"".join([
            struct.pack("<I", len(time_stamps_array)),
            time_stamps_array.tobytes(),

            struct.pack("<I", len(edges)),
            edges.tobytes(),
            # Adjacency list (flattened)
            struct.pack("<I", len(adj_concat_arr)),
            adj_concat_arr.tobytes(),
            struct.pack("<I", len(adj_offsets_arr)),
            adj_offsets_arr.tobytes(),
        ])



        # ------------------------------------------------------------------
        # LAYER 2 — node meta (costs + op_types + paths + value_type_indicators)
        # ------------------------------------------------------------------
        costs = np.zeros(N, dtype=np.int32)

        op_types_concat = []
        op_types_offsets = [0]

        paths_concat = []
        paths_offsets = [0]

        value_type_indicators = []  # 0=primitive, 1=complex (parallel to flattened values)

        for i, (_, node) in enumerate(patches):
            costs[i] = node.cost

            op_types_concat.extend(node.op_types)
            op_types_offsets.append(len(op_types_concat))

            paths_concat.extend(node.paths)
            paths_offsets.append(len(paths_concat))

            # Record type of each value in this node
            for v in node.values:
                if is_primitive_container(v):
                    value_type_indicators.append(0)
                else:
                    value_type_indicators.append(1)

        op_types_arr = np.array(op_types_concat, dtype=np.int8)
        op_types_offsets_arr = np.array(op_types_offsets, dtype=np.int32)

        paths_arr = np.array(paths_concat, dtype=np.int32)
        paths_offsets_arr = np.array(paths_offsets, dtype=np.int32)

        value_type_indicators_arr = np.array(value_type_indicators, dtype=np.int8)

        layer2_payload = b"".join([
            # Costs
            struct.pack("<I", len(costs)),
            costs.tobytes(),

            # Op types (variable length per node)
            struct.pack("<I", len(op_types_arr)),
            op_types_arr.tobytes(),
            struct.pack("<I", len(op_types_offsets_arr)),
            op_types_offsets_arr.tobytes(),

            # Paths (variable length per node)
            struct.pack("<I", len(paths_arr)),
            paths_arr.tobytes(),
            struct.pack("<I", len(paths_offsets_arr)),
            paths_offsets_arr.tobytes(),

            # Value type indicators (0=primitive, 1=complex)
            # This array is parallel to the flattened list of ALL values across ALL nodes
            struct.pack("<I", len(value_type_indicators_arr)),
            value_type_indicators_arr.tobytes(),
        ])

        # ------------------------------------------------------------------
        # LAYER 3 — primitive values
        # Stores only values where is_primitive_container(v) == True
        # Access pattern: use value_type_indicators to know when to read from here
        # ------------------------------------------------------------------
        primitive_bytes = bytearray()
        primitive_offsets = [0]
        primitive_types = []

        def primitive_type_enum(v):
            if isinstance(v, bool): return 2
            if isinstance(v, int): return 0
            if isinstance(v, float): return 1
            if isinstance(v, str): return 3
            if isinstance(v, bytes): return 4
            if isinstance(v, list): return 5
            return 6  # dict

        for _, node in patches:
            for v in node.values:
                if is_primitive_container(v):
                    enc = encode_primitive(v)
                    primitive_bytes.extend(enc)
                    primitive_offsets.append(len(primitive_bytes))
                    primitive_types.append(primitive_type_enum(v))

        primitive_offsets_arr = np.array(primitive_offsets, dtype=np.int32)
        primitive_types_arr = np.array(primitive_types, dtype=np.int8)

        layer3_payload = b"".join([
            # Raw msgpack bytes (concatenated)
            struct.pack("<I", len(primitive_bytes)),
            primitive_bytes,

            # Offsets to split the bytes (N+1 offsets for N values)
            struct.pack("<I", len(primitive_offsets_arr)),
            primitive_offsets_arr.tobytes(),

            # Type enum for each primitive value
            struct.pack("<I", len(primitive_types_arr)),
            primitive_types_arr.tobytes(),
        ])

        # ------------------------------------------------------------------
        # LAYER 4 — complex values
        # Stores only values where is_primitive_container(v) == False
        # Access pattern: use value_type_indicators to know when to read from here
        # ------------------------------------------------------------------
        complex_bytes = bytearray()
        complex_offsets = [0]

        for _, node in patches:
            for v in node.values:
                if not is_primitive_container(v):
                    enc = encode_complex(v)
                    complex_bytes.extend(enc)
                    complex_offsets.append(len(complex_bytes))

        complex_offsets_arr = np.array(complex_offsets, dtype=np.int32)

        layer4_payload = b"".join([
            # Raw pickle bytes (concatenated)
            struct.pack("<I", len(complex_bytes)),
            complex_bytes,

            # Offsets to split the bytes (N+1 offsets for N values)
            struct.pack("<I", len(complex_offsets_arr)),
            complex_offsets_arr.tobytes(),
        ])

        # ------------------------------------------------------------------
        # FINAL PACKING (header + 4 layers)
        # ------------------------------------------------------------------
        final = bytearray()
        final.extend(MAGIC)
        final.extend(struct.pack("<I", VERSION))

        def write_block(block_id: int, payload: bytes):
            final.extend(struct.pack("<BQ", block_id, len(payload)))
            final.extend(payload)

        write_block(1, layer1_payload)
        write_block(2, layer2_payload)
        write_block(3, layer3_payload)
        write_block(4, layer4_payload)

        # store uncompressed in memory – write_full_to_disk() will compress it
        self._patch_graph_b = bytes(final)