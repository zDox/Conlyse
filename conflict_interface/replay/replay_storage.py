from __future__ import annotations

import pickle
import struct
from array import array
from pathlib import Path
from typing import TYPE_CHECKING

import lz4.frame
import msgpack
import numpy as np

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.replay.custom_data_types import PATCH_INDEX_DTYPE
from conflict_interface.replay.metadata import Metadata
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree
from conflict_interface.replay.path_tree import PathTree
from conflict_interface.replay.path_tree_node import PathTreeNode
from conflict_interface.utils.binary import BinaryReader
from conflict_interface.utils.binary import BinaryWriter

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface


class ReplayStorage:
    path_tree: PathTree | None

    def __init__(self):
        self._metadata_b: bytes | None = None
        self._initial_game_state_b: bytes | None = None
        self._static_map_data_b: bytes | None = None
        self._path_tree_b: bytes | None = None
        self._patch_index_b: bytes | None = None
        self._d_pool_b: bytes | None = None
        self._last_game_state_b: bytes | None = None

        self.metadata: Metadata | None = None
        self.initial_game_state: GameState | None = None
        self.static_map_data: StaticMapData | None = None
        self.path_tree: PathTree | None = None
        self.patch_graph: PatchGraph | None = None
        self.last_game_state: GameState | None = None

        self.compressor = lz4.frame.compress
        self.decompressor = lz4.frame.decompress

    def read_full_from_disk(self, file_path: Path):
        def read_compressed(r) -> bytes:
            l = r.read_int32()

            compressed = r.read_bytes(l)
            return self.decompressor(compressed)

        with open(file_path, 'rb') as f:
            data = f.read()

        reader = BinaryReader(data)
        length = reader.read_int32()
        self._metadata_b = reader.read_bytes(length)

        self._initial_game_state_b = read_compressed(reader)
        self._static_map_data_b = read_compressed(reader)
        self._path_tree_b = read_compressed(reader)

        length = reader.read_int32()
        self._patch_index_b = reader.read_bytes(length)
        print(f"Data pool size according to patch_index {sum(x['size'] for x in np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE))}")
        print(np.frombuffer(self._patch_index_b, dtype = PATCH_INDEX_DTYPE))
        length = reader.read_int32()
        self._d_pool_b = reader.read_bytes(length)

        length = reader.read_int32()
        print(f"Last gamestate length compressed {length}")
        compressed = reader.read_bytes(length)
        print(f"Actual length {len(compressed)}")
        self._last_game_state_b = self.decompressor(compressed)

    def read_append_mode_from_disk(self, file_path: Path):
        with open(file_path, 'rb') as f:
            data = f.read()

        reader = BinaryReader(data)

        length = reader.read_int32()
        self._metadata_b = reader.read_bytes(length)

        length = reader.read_int32()
        reader.skip(length)

        length = reader.read_int32()
        reader.skip(length)

        length = reader.read_int32()
        compressed = reader.read_bytes(length)
        self._path_tree_b =  self.decompressor(compressed)

        length = reader.read_int32()
        self._patch_index_b = reader.read_bytes(length)

        length = reader.read_int32()
        self._d_pool_b = reader.read_bytes(length)

        length = reader.read_int32()
        compressed = reader.read_bytes(length)
        self._last_game_state_b = self.decompressor(compressed)

    def read_metadata_from_disk(self, file_path):
        with open(file_path, "rb") as f:
            len_metadata = struct.unpack_from('<i', f.read(4), 0)[0]
            self._metadata_b = f.read(len_metadata)

    def write_full_to_disk(self, file_path: Path):
        def write_compressed(writer ,b):
            c = self.compressor(b)
            writer.write_int32(len(c))
            writer.write_bytes(c)

        print("Saving")
        assert self._initial_game_state_b is not None, "Initial game state is not recorded in the replay."
        assert self._static_map_data_b is not None, "Static map data is not recorded in the replay."
        assert self._path_tree_b is not None, "No Path Tree to put into memory"
        assert self._patch_index_b is not None, "Patch graph metadat has not been read."
        assert self._d_pool_b is not None, "Data pool has not been read"
        assert self._last_game_state_b is not None, "Last Game state has not been set"

        data = BinaryWriter()
        data.write_int32(Metadata.size)
        data.seek(Metadata.size+4)# Space holder for metadata
        write_compressed(data, self._initial_game_state_b)
        write_compressed(data, self._static_map_data_b)
        write_compressed(data, self._path_tree_b)

        data.write_int32(len(self._patch_index_b))
        patch_index_start = data.tell()
        data.write_bytes(self._patch_index_b)

        data.write_int32(len(self._d_pool_b))
        data.write_bytes(self._d_pool_b)
        write_compressed(data, self._last_game_state_b)

        with open(file_path, 'wb') as f:
            f.write(data.getbuffer())

        self.metadata.patch_index_start = patch_index_start
        self.update_metadata(file_path)

    def write_last_game_state(self, file_path: Path):
        assert self._last_game_state_b is not None, "Last Game State is None cannot write"
        compressed = self.compressor(self._last_game_state_b)
        length = len(compressed)
        print(f"Last gamestate length: {length}")
        with open(file_path, 'r+b') as f:
            f.seek(self.metadata.patch_index_start + len(self._patch_index_b))
            current_size = struct.unpack_from('<i', f.read(4), 0)[0]
            new_data_start_pos = self.metadata.patch_index_start + len(self._patch_index_b) + current_size+4
            f.seek(new_data_start_pos)
            print(f"Before last gamestate write. {new_data_start_pos}")
            f.write(struct.pack('<i', length))
            f.write(compressed)
            print(f"File pos after last_gs_write: {f.tell()}")

    def update_metadata(self, file_path: Path):
        with open(file_path, "r+b") as f:
            len_metadata = struct.unpack_from('<i', f.read(4), 0)[0]
            metadata_b = self.metadata.serialize()
            assert(len_metadata == len(metadata_b)), "Metadat has changed length"
            f.write(metadata_b)

    def append_patches_to_disk(self, nodes: list[PatchGraphNode], paths: list[list[tuple[int, int, str | int]]], file_path: Path):
        # update patch index
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        patch_index = np.copy(patch_index)
        data = BinaryWriter()
        index_offset = self.metadata.current_patches

        for i,patch in enumerate(nodes):
            if index_offset+i == 0: offset = 0
            else: offset = patch_index[index_offset+i-1]['offset'] + patch_index[index_offset+i-1]['size']

            patch_s: memoryview = patch.serialize(paths[i])
            size = len(patch_s)
            patch_index[i+index_offset]['offset'] = offset
            patch_index[i+index_offset]['size'] = size
            data.write_bytes(patch_s)
            self.metadata.current_patches+=1

        self._patch_index_b = patch_index.tobytes()

        with open(file_path, 'r+b') as f:
            f.seek(self.metadata.patch_index_start + len(self._patch_index_b))
            current_size = struct.unpack_from('<i', f.read(4), 0)[0]
            new_data_start_pos = self.metadata.patch_index_start + len(self._patch_index_b) + current_size +4
            print(f"patch_index_start: {self.metadata.patch_index_start}")
            print(f"new data start pos: {new_data_start_pos}")
            f.seek(new_data_start_pos)
            print(f"Length of acatual data: {len(data.getbuffer())}")
            f.write(data.getbuffer())
            print(f"Position after write: {f.tell()}")

        with open(file_path, 'r+b') as f:
            f.seek(self.metadata.patch_index_start)
            print(f"Writing patch_index {str(patch_index)[:100]} of size: {len(self._patch_index_b)}")
            f.write(self._patch_index_b)

        with open(file_path, 'r+b') as f:
            f.seek(self.metadata.patch_index_start + len(self._patch_index_b))
            current_size = struct.unpack_from('<i', f.read(4), 0)[0]
            print(f"Current data pool size: {current_size}")
            new_size = current_size + len(data.getbuffer())
            print(f"Writing new size: {new_size}")
            f.seek(self.metadata.patch_index_start + len(self._patch_index_b))
            f.write(struct.pack('<i', new_size))

    def initialize(self, max_patches):
        self.metadata = Metadata(
            start_time = 0,
            last_time = 0,
            max_patches=max_patches,
            current_patches=0,
            patch_index_start=0,
            is_fragmented=False
        )
        self.path_tree = PathTree()
        self.patch_graph = PatchGraph()
        self._patch_index_b = np.zeros(max_patches, dtype=PATCH_INDEX_DTYPE)

    def load_metadata(self) -> Metadata:
        if self._metadata_b is None:
            raise ValueError("Metadata is not recorded in the replay.")
        self.metadata = Metadata.deserialize(self._metadata_b)
        return self.metadata

    def load_initial_game_state(self, game: ReplayInterface | None) -> GameState:
        if self._initial_game_state_b is None:
            raise ValueError("Initial game state is not recorded in the replay.")

        self.initial_game_state =  pickle.loads(self._initial_game_state_b)
        if game is not None:
            GameObject.set_game_recursive(self.initial_game_state, game)
        return self.initial_game_state

    def load_last_game_state(self) -> GameState:
        if self._last_game_state_b is None:
            raise ValueError("Last game state is not recorded in the replay.")

        self.last_game_state = pickle.loads(self._last_game_state_b)
        return self.last_game_state

    def load_static_map_data(self, game: ReplayInterface | None) -> StaticMapData:
        if self._static_map_data_b is None:
            raise ValueError("Static map data is not recorded in the replay.")
        self.static_map_data = pickle.loads(self._static_map_data_b)
        if game is not None:
            GameObject.set_game_recursive(self.static_map_data, game)
        return self.static_map_data

    def load_path_tree(self) -> PathTree:
        if self._path_tree_b is None:
            raise ValueError("Path Tree is not recorded in the replay.")

        n, path_elements, parent_bytes, is_leaf_bytes = msgpack.unpackb(self._path_tree_b, raw=False)

        parent_indices = array('i')
        parent_indices.frombytes(parent_bytes)

        is_leaf_flags = array('B')
        is_leaf_flags.frombytes(is_leaf_bytes)

        self.path_tree = PathTree()
        self.path_tree.idx_counter = n

        # Create all nodes O(n)
        for idx in range(1,n):
            node = PathTreeNode(
                path_element=path_elements[idx],
                index=idx,
                parent=None
            )
            node.is_leaf = bool(is_leaf_flags[idx])
            self.path_tree.idx_to_node[idx] = node

        # Link relationships O(n)

        for idx in range(n):
            parent_idx = parent_indices[idx]
            if parent_idx != -1:
                if parent_idx == 0:
                    pass
                self.path_tree.idx_to_node[idx].parent = self.path_tree.idx_to_node[parent_idx]
                self.path_tree.idx_to_node[parent_idx].children[path_elements[idx]] = self.path_tree.idx_to_node[idx]

        if not self.metadata.is_fragmented: return self.path_tree
        
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        data_pool = memoryview(self._d_pool_b)
        
        for offset, size in patch_index:
            if size == 0: break
            
            patch_data = data_pool[offset:offset+size]
            new_paths = PatchGraphNode.extract_tree_nodes(patch_data)

            if len(new_paths) == 0:
                continue

            for p in new_paths:
                self.path_tree.add_node(p[0], self.path_tree.idx_to_node[p[1]], p[2])

        return self.path_tree

    def load_patches(self, game: ReplayInterface) -> PatchGraph:
        self.patch_graph = PatchGraph()
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        data_pool = memoryview(self._d_pool_b)
        for offset, size in patch_index:
            if size == 0: break
            patch_data = data_pool[offset:offset + size]
            patch, _ = PatchGraphNode.deserialize(patch_data, game)
            self.patch_graph.add_patch_node_fast(patch)

        return self.patch_graph

    def unload_metadata(self):
        self._metadata_b = pickle.dumps(self.metadata)

    def unload_initial_game_state(self, game_state: GameState):
        game = game_state.game
        GameObject.set_game_recursive(game_state, None)
        self._initial_game_state_b = pickle.dumps(game_state)
        GameObject.set_game_recursive(game_state, game)
        self.initial_game_state = game_state

    def unload_last_game_state(self):
        assert self.last_game_state is not None, "No GameState provided."
        assert self.last_game_state.game is None, "Last game state has game set"
        self._last_game_state_b = pickle.dumps(self.last_game_state)

    def unload_static_map_data(self, static_map_data: StaticMapData):
        game = static_map_data.game
        GameObject.set_game_recursive(static_map_data, None)
        self._static_map_data_b = pickle.dumps(static_map_data)
        GameObject.set_game_recursive(static_map_data, game)
        self.static_map_data = static_map_data

    def unload_path_tree(self):
        n = self.path_tree.idx_counter
        path_elements = [None] * n
        parent_indices = array('i', [-1] * n)  # signed int array
        is_leaf_flags = array('B', [0] * n)  # byte array for booleans

        for idx, node in self.path_tree.idx_to_node.items():
            path_elements[idx] = node.path_element
            parent_indices[idx] = node.parent.index if node.parent else -1
            is_leaf_flags[idx] = 1 if node.is_leaf else 0

        self._path_tree_b = msgpack.packb([
            n,
            path_elements,
            parent_indices.tobytes(),
            is_leaf_flags.tobytes()
        ], use_bin_type=True)

    def unload_patches(self):
        patches = self.patch_graph.patches.items()
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        patch_index = np.copy(patch_index)
        data_pool = BinaryWriter()

        for i, ((_, _), patch) in enumerate(patches):
            if i == 0: offset = 0
            else: offset = patch_index[i-1]['offset'] + patch_index[i-1]['size']
            patch_s: memoryview = patch.serialize([])
            size = len(patch_s)
            patch_index[i]['offset'] = offset
            patch_index[i]['size'] = size
            data_pool.write_bytes(patch_s)
            self.metadata.current_patches += 1

        self._patch_index_b = patch_index.tobytes()
        self._d_pool_b = data_pool.getbuffer()



