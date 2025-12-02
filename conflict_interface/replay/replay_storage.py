from __future__ import annotations

import pickle
import struct
from pathlib import Path
from typing import TYPE_CHECKING

import lz4.frame
import numpy as np

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.replay.custom_data_types import PATCH_INDEX_DTYPE
from conflict_interface.replay.metadata import Metadata
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.path_tree import PathTree
from conflict_interface.utils.binary import BinaryReader
from conflict_interface.utils.binary import BinaryWriter

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface


class ReplayStorage:
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

        self._d_pool_b = read_compressed(reader)
        self._last_game_state_b = read_compressed(reader)

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
        compressed = reader.read_bytes(length)
        self._d_pool_b = self.decompressor(compressed)

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
        data.write_int32(20)
        data.seek(24)# Space holder for metadata
        write_compressed(data, self._initial_game_state_b)
        write_compressed(data, self._static_map_data_b)
        write_compressed(data, self._path_tree_b)

        data.write_int32(len(self._patch_index_b))
        patch_index_start = data.tell()
        data.write_bytes(self._patch_index_b)

        write_compressed(data, self._d_pool_b)
        write_compressed(data, self._last_game_state_b)

        with open(file_path, 'wb') as f:
            f.write(data.getbuffer())

        self.metadata.patch_index_start = patch_index_start
        self.update_metadata(file_path)

    def write_last_game_state(self, file_path: Path):
        assert self._last_game_state_b is not None, "Last Game State is None cannot write"
        compressed = self.compressor(self._last_game_state_b)
        length = len(compressed)
        with open(file_path, 'ab') as f:
            f.write(struct.pack('>I', length))
            f.write(compressed)

    def update_metadata(self, file_path: Path):
        with open(file_path, "r+b") as f:
            len_metadata = struct.unpack_from('<i', f.read(4), 0)[0]
            metadata_b = self.metadata.serialize()
            assert(len_metadata == len(metadata_b)), "Metadat has changed length"
            f.write(metadata_b)

    def append_patches_to_disk(self, nodes: list[PatchGraphNode], paths: list[list[list[int| str]]], file_path: Path):
        # update patch index
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        data = BinaryWriter()
        index_offset = self.metadata.current_patches

        for i,patch in enumerate(nodes):
            offset = data.tell()
            patch_s: memoryview = patch.serialize(paths[i])
            size = len(patch_s)
            patch_index[i+index_offset]['offset'] = offset
            patch_index[i+index_offset]['size'] = size
            data.write_bytes(patch_s)
            self.metadata.current_patches+=1

        with open(file_path, 'ab') as f:
            f.write(data.getbuffer())

        with open(file_path, 'r+b') as f:
            f.seek(self.metadata.current_patches)
            data.write_bytes(patch_index.tobytes())

    def initialize(self, max_patches):
        self.metadata = Metadata(
            start_time = 0,
            last_time = 0,
            max_patches=max_patches,
            current_patches=0,
            patch_index_start=0,
        )
        self.path_tree = PathTree()
        self.patch_graph = PatchGraph()

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
        self.path_tree = pickle.loads(self._path_tree_b)
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)

        data_pool = memoryview(self._d_pool_b)

        for offset, size in patch_index:
            patch_data = data_pool[offset:offset+size]
            if size == 0: break
            original_paths = PatchGraphNode.extract_tree_nodes(patch_data)

            if len(original_paths) == 0:
                continue

            for p in original_paths:
                self.path_tree.get_or_add_path_node(p)

        return self.path_tree

    def load_patches(self, game: ReplayInterface) -> PatchGraph:
        self.patch_graph = PatchGraph()
        patch_index = np.frombuffer(self._patch_index_b, dtype=PATCH_INDEX_DTYPE)
        data_pool = memoryview(self._d_pool_b)
        for offset, size in patch_index:
            if size == 0: break
            patch_data = data_pool[offset:offset + size]
            patch, original_paths = PatchGraphNode.deserialize(patch_data, game)

            for p in original_paths:
                self.path_tree.get_or_add_path_node(p)

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
        self._path_tree_b = pickle.dumps(self.path_tree)

    def unload_patches(self):
        patches = self.patch_graph.patches.items()
        patch_index = np.zeros(self.metadata.max_patches, dtype=PATCH_INDEX_DTYPE)
        data_pool = BinaryWriter()

        for i, ((_, _), patch) in enumerate(patches):
            offset = data_pool.tell()
            patch_s: memoryview = patch.serialize([])
            size = len(patch_s)
            patch_index[i]['offset'] = offset
            patch_index[i]['size'] = size
            data_pool.write_bytes(patch_s)
            self.metadata.current_patches += 1

        self._patch_index_b = patch_index.tobytes()
        self._d_pool_b = data_pool.getbuffer()



