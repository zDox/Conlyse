from __future__ import annotations

import pickle
import struct
from array import array
from logging import getLogger
from typing import TYPE_CHECKING
from typing import cast

import lz4.frame
import msgpack
import numpy as np

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import GameObjectSerializer
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.replay.constants import PATCH_INDEX_DTYPE
from conflict_interface.replay.metadata import Metadata
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree
from conflict_interface.replay.path_tree_node import PathTreeNode
from conflict_interface.utils.binary import BinaryReader
from conflict_interface.utils.binary import BinaryWriter

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface

logger = getLogger()


class ReplayStorage:
    """
    Manages persistent storage of game replay data using a custom binary format.

    The storage system uses a hybrid compression approach:
    - Some data is compressed with LZ4 for space efficiency
    - Some data remains uncompressed for random access (metadata, patch index)

    Supports two modes:
    1. Full mode: Complete replay with all data
    2. Append mode: Allows adding new patches to existing replays
    """

    path_tree: PathTree | None

    def __init__(self, data: bytearray, version):
        # Binary representations of serialized data (compressed or raw)
        self._data_b: bytearray = data
        self._metadata_b: bytes | None = None
        self._initial_game_state_b: bytes | None = None
        self._static_map_data_b: bytes | None = None
        self._path_tree_b: bytes | None = None
        self._patch_index_b: bytes | None = None
        self._d_pool_b: bytes | None = None  # Data pool containing all patches
        self._last_game_state_b: bytes | None = None

        # Deserialized objects for in-memory use
        self.metadata: Metadata | None = None
        self.initial_game_state: GameState | None = None
        self.static_map_data: StaticMapData | None = None
        self.path_tree: PathTree | None = None
        self.patch_graph: PatchGraph | None = None
        self.last_game_state: GameState | None = None

        # Compression utilities using LZ4 for fast compression/decompression
        self.compressor = lz4.frame.compress
        self.decompressor = lz4.frame.decompress
        self.serializer = GameObjectSerializer(version)

    def extend(self, required_size):
        if len(self._data_b)<required_size:
            self._data_b.extend(b'\x00' * (required_size - len(self._data_b)))

    def read_all(self):
        """
        Reads the complete replay file from disk into memory.

        File structure (in order):
        1. Metadata (uncompressed, fixed size)
        2. Initial game state (LZ4 compressed)
        3. Static map data (LZ4 compressed)
        4. Path tree (LZ4 compressed)
        5. Patch index (uncompressed for random access)
        6. Data pool (uncompressed patches)
        7. Last game state (LZ4 compressed)
        """

        def read_compressed(r) -> bytes:
            """Helper to read length-prefixed compressed data."""
            l = r.read_int32()
            c = r.read_bytes(l)
            return self.decompressor(c)

        # Load entire file into memory
        data = self._data_b

        reader = BinaryReader(data)

        # Read metadata (uncompressed)
        length = reader.read_int32()
        self._metadata_b = reader.read_bytes(length)

        # Read compressed sections
        self._initial_game_state_b = read_compressed(reader)
        self._static_map_data_b = read_compressed(reader)
        self._path_tree_b = read_compressed(reader)

        # Read patch index (uncompressed for direct access)
        length = reader.read_int32()
        self._patch_index_b = reader.read_bytes(length)

        # Read data pool containing all patch data
        length = reader.read_int32()
        self._d_pool_b = reader.read_bytes(length)

        # Read last game state (compressed)
        self._last_game_state_b = read_compressed(reader)

    def read_append_mode_from_disk(self):
        """
        Reads only the portions of the replay needed for append mode.
        Skips initial game state and static map data since they won't change.

        Used when continuing to record an ongoing game replay.
        """
        data = self._data_b

        reader = BinaryReader(data)

        # Read metadata
        length = reader.read_int32()
        self._metadata_b = reader.read_bytes(length)

        # Skip initial game state (not needed for appending)
        length = reader.read_int32()
        reader.skip(length)

        # Skip static map data (not needed for appending)
        length = reader.read_int32()
        reader.skip(length)

        # Read and decompress path tree
        length = reader.read_int32()
        compressed = reader.read_bytes(length)
        self._path_tree_b = self.decompressor(compressed)

        # Read patch index
        length = reader.read_int32()
        self._patch_index_b = reader.read_bytes(length)

        # Read data pool
        length = reader.read_int32()
        self._d_pool_b = reader.read_bytes(length)

        # Read and decompress last game state
        length = reader.read_int32()
        compressed = reader.read_bytes(length)
        self._last_game_state_b = self.decompressor(compressed)

    def read_metadata_from_disk(self):
        """
        Quickly reads just the metadata without loading the entire replay.
        Useful for listing replays or checking replay properties.
        """
        len_metadata = struct.unpack_from('<i', self._data_b, 0)[0]
        self._metadata_b = self._data_b[4:4+len_metadata]

    def write_all(self):
        """
        Writes the complete replay to disk in the binary format.

        Layout:
        - Metadata at fixed position for quick updates
        - Compressed game data
        - Uncompressed patch index for random access
        - Uncompressed data pool for append mode
        """

        def write_compressed(writer, b):
            """Helper to write compressed data with length prefix."""
            c = self.compressor(b)
            writer.write_int32(len(c))
            writer.write_bytes(c)

        # Validate all required data is present
        assert self._initial_game_state_b is not None, "Initial game state is not recorded in the replay."
        assert self._static_map_data_b is not None, "Static map data is not recorded in the replay."
        assert self._path_tree_b is not None, "No Path Tree to put into memory"
        assert self._patch_index_b is not None, "Patch graph metadata has not been read."
        assert self._d_pool_b is not None, "Data pool has not been read"
        assert self._last_game_state_b is not None, "Last Game state has not been set"

        data = BinaryWriter()

        # Reserve space for metadata at the beginning (fixed size for easy updates)
        data.write_int32(Metadata.size)
        data.seek(Metadata.size + 4)  # Skip ahead to leave placeholder

        # Write compressed game data
        write_compressed(data, self._initial_game_state_b)
        write_compressed(data, self._static_map_data_b)
        write_compressed(data, self._path_tree_b)

        # Write patch index uncompressed (enables direct indexing)
        data.write_int32(len(self._patch_index_b))
        patch_index_start = data.tell()  # Store position for metadata
        data.write_bytes(self._patch_index_b)

        # Write data pool uncompressed (allows appending new patches)
        data.write_int32(len(self._d_pool_b))
        data.write_bytes(self._d_pool_b)

        # Write compressed last game state
        write_compressed(data, self._last_game_state_b)

        # Write to file
        self._data_b[:] = data.getbuffer()

        # Update metadata with patch index location and write it
        self.metadata.patch_index_start = patch_index_start
        self.update_metadata()

    def write_last_game_state(self):
        """
        Updates only the last game state in an existing replay file.
        Uses in-place update to avoid rewriting the entire file.
        """
        assert self._last_game_state_b is not None, "Last Game State is None cannot write"

        compressed = self.compressor(self._last_game_state_b)
        length = len(compressed)

        # Navigate to the end of the data pool
        end_of_patch_index = self.metadata.patch_index_start + len(self._patch_index_b)
        current_size = struct.unpack_from('<i', self._data_b, end_of_patch_index)[0]
        new_data_start_pos = self.metadata.patch_index_start + len(self._patch_index_b) + current_size + 4

        # Write the compressed last game state
        self.extend(new_data_start_pos+4+length)
        struct.pack_into('<i', self._data_b, new_data_start_pos,length)
        self._data_b[new_data_start_pos + 4 : new_data_start_pos + 4 + length] = compressed

    def update_metadata(self):
        """
        Updates the metadata section at the beginning of the file.
        Since metadata is fixed size, this is a simple overwrite.
        """
        len_metadata = struct.unpack_from('<i', self._data_b, 0)[0]
        metadata_b = self.metadata.serialize()
        assert (len_metadata == len(metadata_b)), "Metadata has changed length"
        self._data_b[4: 4+len_metadata] = metadata_b

    def append_patches_to_disk(self, nodes: list[PatchGraphNode], paths: list[list[tuple[int, int, str | int]]]):
        """
        Appends new patch nodes to an existing replay file.

        This allows recording additional game events without rewriting the entire file.
        Updates both the patch index and data pool in place.

        Args:
            nodes: New patch nodes to append
            paths: Path information for each node
        """
        # Load and copy the patch index
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        patch_index = np.copy(patch_index)

        patch_bytes = BinaryWriter()
        index_offset = self.metadata.current_patches

        assert len(paths) == len(nodes), "Not a paths list for every node"


        # Serialize each patch and update the index
        for i, patch in enumerate(nodes):
            # Calculate offset based on previous patch
            if index_offset + i == 0:
                offset = 0
            else:
                offset = patch_index[index_offset + i - 1]['offset'] + patch_index[index_offset + i - 1]['size']

            # Serialize patch and record its position
            patch_s: memoryview = patch.serialize(paths[i], self.serializer)
            size = len(patch_s)
            patch_index[i + index_offset]['offset'] = offset
            patch_index[i + index_offset]['size'] = size
            patch_bytes.write_bytes(patch_s)
            self.metadata.current_patches += 1

        # Update cached patch index
        self._patch_index_b = patch_index.tobytes()

        # Find where to append the new patches
        end_of_patch_index = self.metadata.patch_index_start + len(self._patch_index_b)
        current_size = struct.unpack_from('<i', self._data_b, end_of_patch_index)[0]
        new_data_start_pos = self.metadata.patch_index_start + len(self._patch_index_b) + current_size + 4

        # Append patch data
        self.extend(new_data_start_pos+len(patch_bytes.getbuffer()))
        self._data_b[new_data_start_pos: new_data_start_pos+len(patch_bytes.getbuffer())] = patch_bytes.getbuffer()
        # Update patch index in file
        self._data_b[self.metadata.patch_index_start : self.metadata.patch_index_start+len(self._patch_index_b)] = self._patch_index_b


        # Update data pool size
        new_size = current_size + len(patch_bytes.getbuffer())
        struct.pack_into('<i', self._data_b, self.metadata.patch_index_start + len(self._patch_index_b), new_size)



    def initialize(self, max_patches):
        """
        Initializes a new replay storage with empty data structures.

        Args:
            max_patches: Maximum number of patches the replay can hold
        """
        self.metadata = Metadata(
            start_time=0,
            last_time=0,
            max_patches=max_patches,
            current_patches=0,
            patch_index_start=0,
            is_fragmented=False
        )
        self.path_tree = PathTree()
        self.patch_graph = PatchGraph()
        # Pre-allocate patch index array
        self._patch_index_b = np.zeros(max_patches, dtype=PATCH_INDEX_DTYPE)

    def load_metadata(self) -> Metadata:
        """Deserializes and returns the replay metadata."""
        if self._metadata_b is None:
            raise ValueError("Metadata is not recorded in the replay.")
        self.metadata = Metadata.deserialize(self._metadata_b)
        return self.metadata

    def load_initial_game_state(self, game: ReplayInterface | None) -> GameState:
        """
        Deserializes the initial game state from the replay.

        Args:
            game: Optional replay interface to link game objects to
        """
        if self._initial_game_state_b is None:
            raise ValueError("Initial game state is not recorded in the replay.")

        self.initial_game_state = self.serializer.deserialize(self._initial_game_state_b)
        if game is not None:
            # Link game objects back to the replay interface
            GameObject.set_game_recursive(self.initial_game_state, game)
        self.initial_game_state = cast(GameState, self.initial_game_state)
        return self.initial_game_state

    def load_last_game_state(self) -> GameState:
        """Deserializes the last recorded game state."""
        if self._last_game_state_b is None:
            raise ValueError("Last game state is not recorded in the replay.")

        self.last_game_state = pickle.loads(self._last_game_state_b)
        return self.last_game_state

    def load_static_map_data(self, game: ReplayInterface | None) -> StaticMapData:
        """
        Deserializes static map data (terrain, objectives, etc.).

        Args:
            game: Optional replay interface to link game objects to
        """
        if self._static_map_data_b is None:
            raise ValueError("Static map data is not recorded in the replay.")
        self.static_map_data = self.serializer.deserialize(self._static_map_data_b)
        if game is not None:
            GameObject.set_game_recursive(self.static_map_data, game)
        self.static_map_data = cast(StaticMapData, self.static_map_data)
        return self.static_map_data

    def load_path_tree(self) -> PathTree:
        """
        Deserializes the path tree structure used for tracking object paths.

        The path tree is stored in a compact format with separate arrays for:
        - Path elements (the actual path components)
        - Parent indices (tree structure)
        - Leaf flags (optimization for traversal)

        For fragmented replays, also reconstructs paths from patches.
        """
        if self._path_tree_b is None:
            raise ValueError("Path Tree is not recorded in the replay.")

        # Unpack the compact representation
        n, path_elements, parent_bytes, is_leaf_bytes = msgpack.unpackb(self._path_tree_b, raw=False)

        # Reconstruct arrays from bytes
        parent_indices = array('i')
        parent_indices.frombytes(parent_bytes)

        is_leaf_flags = array('B')
        is_leaf_flags.frombytes(is_leaf_bytes)

        self.path_tree = PathTree()
        self.path_tree.idx_counter = n

        # Create all nodes (O(n) time)
        for idx in range(1, n):
            node = PathTreeNode(
                path_element=path_elements[idx],
                index=idx,
                parent=None
            )
            node.is_leaf = bool(is_leaf_flags[idx])
            self.path_tree.idx_to_node[idx] = node

        # Link parent-child relationships (O(n) time)
        for idx in range(n):
            parent_idx = parent_indices[idx]
            if parent_idx != -1 and parent_idx != 0:
                self.path_tree.idx_to_node[idx].parent = self.path_tree.idx_to_node[parent_idx]
                self.path_tree.idx_to_node[parent_idx].children[path_elements[idx]] = self.path_tree.idx_to_node[idx]


        if not self.metadata.is_fragmented:
            return self.path_tree

        # Handle fragmented replays by extracting paths from patches
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        data_pool = memoryview(self._d_pool_b)

        # Reconstruct missing paths from patch data
        for offset, size in patch_index:
            if size == 0:
                break

            patch_data = data_pool[offset:offset + size]
            new_paths = PatchGraphNode.extract_tree_nodes(patch_data)

            if len(new_paths) == 0:
                continue

            for p in new_paths:
                self.path_tree.add_node(p[0], self.path_tree.idx_to_node[p[1]], p[2])

        return self.path_tree

    def load_patches(self, game: ReplayInterface) -> PatchGraph:
        """
        Loads all patches from the data pool and builds the patch graph.

        The patch graph represents the timeline of game state changes.
        Each patch contains deltas that can be applied to transition between states.

        Args:
            game: Replay interface for linking game objects
        """
        self.patch_graph = PatchGraph()

        # Access the patch index and data pool
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        data_pool = memoryview(self._d_pool_b)

        if len(data_pool) == 0:
            logger.warning("No patches found in replay.")
            return self.patch_graph

        # Deserialize each patch and add to graph
        for offset, size in patch_index:
            if size == 0:
                break  # Reached end of valid patches
            patch_data = data_pool[offset:offset + size]
            patch, _ = PatchGraphNode.deserialize(patch_data, game, self.serializer)
            self.patch_graph.add_edge_and_vertices(patch)

        return self.patch_graph

    def unload_metadata(self):
        """Serializes metadata to bytes for storage."""
        self._metadata_b = self.metadata.serialize()

    def unload_initial_game_state(self, game_state: GameState):
        """
        Serializes the initial game state using pickle.

        Temporarily removes game references to avoid circular serialization,
        then restores them after pickling.
        """
        self._initial_game_state_b = self.serializer.serialize_game_object(game_state)
        self.initial_game_state = game_state

    def unload_last_game_state(self):
        """Serializes the last game state using pickle."""
        assert self.last_game_state is not None, "No GameState provided."
        assert self.last_game_state.game is None, "Last game state has game set"
        self._last_game_state_b = pickle.dumps(self.last_game_state)

    def unload_static_map_data(self, static_map_data: StaticMapData):
        """
        Serializes static map data using pickle.

        Temporarily removes game references before serialization.
        """
        self._static_map_data_b = self.serializer.serialize_game_object(static_map_data)
        self.static_map_data = static_map_data

    def unload_path_tree(self):
        """
        Serializes the path tree into a compact binary representation.

        Uses parallel arrays for efficient storage:
        - Path elements: actual path data
        - Parent indices: tree structure
        - Leaf flags: boolean flags for optimization

        Packed with msgpack for additional compression.
        """
        n = self.path_tree.idx_counter  # Total number of nodes
        path_elements: list[int | str | None] = [None] * n
        parent_indices = array('i', [-1] * n)  # Signed integer array
        is_leaf_flags = array('B', [0] * n)  # Byte array for booleans

        # Extract data from each node
        for idx, node in self.path_tree.idx_to_node.items():
            path_elements[idx] = node.path_element
            parent_indices[idx] = node.parent.index if node.parent else -1
            is_leaf_flags[idx] = 1 if node.is_leaf else 0

        # Pack into compact binary format
        self._path_tree_b = msgpack.packb([
            n,
            path_elements,
            parent_indices.tobytes(),
            is_leaf_flags.tobytes()
        ], use_bin_type=True)

    def unload_patches(self):
        """
        Serializes all patches from the patch graph into the data pool.

        Builds the patch index that maps each patch to its location in the pool,
        enabling random access to any patch without deserializing everything.
        """
        patches = self.patch_graph.patches.items()

        # Load and copy the patch index
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        patch_index = np.copy(patch_index)

        data_pool = BinaryWriter()

        # Serialize each patch and record its position
        for i, (_, patch) in enumerate(patches):
            # Calculate offset based on previous patches
            if i == 0:
                offset = 0
            else:
                offset = patch_index[i - 1]['offset'] + patch_index[i - 1]['size']

            # Serialize and store patch
            patch_s: memoryview = patch.serialize([], self.serializer)
            size = len(patch_s)
            patch_index[i]['offset'] = offset
            patch_index[i]['size'] = size
            data_pool.write_bytes(patch_s)
            self.metadata.current_patches += 1

        # Store serialized data
        self._patch_index_b = patch_index.tobytes()
        self._d_pool_b = data_pool.getbuffer()