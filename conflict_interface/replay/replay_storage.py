from __future__ import annotations

import os
import pickle
import struct
from pathlib import Path
from typing import TYPE_CHECKING

import lz4.frame

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.replay.metadata import Metadata
from conflict_interface.replay.patch_graph import PatchGraph
from conflict_interface.replay.path_tree import PathTree

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface


class ReplayStorage:
    def __init__(self):
        self._metadata_b: bytes | None = None
        self._initial_game_state_b: bytes | None = None
        self._static_map_data_b: bytes | None = None
        self._patch_graph_b: bytes | None = None
        self._d_pool_b: bytes | None = None

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
        self._patch_graph_b = data[3]
        self._d_pool_b = data[4]

    def read_append_mode_from_disk(self, file_path: Path):
        data = []
        idx_to_read = (0,3,4)
        with open(file_path, 'rb') as f:
            i = 0
            while True:
                length_bytes = f.read(4)
                if not length_bytes:
                    break

                if i not in idx_to_read:
                    i+=1
                    continue

                (length,) = struct.unpack('>I', length_bytes)
                compressed = f.read(length)
                decompressed = self.decompressor(compressed)
                data.append(decompressed)
                i += 1

        self._metadata_b = data[0]
        self._patch_graph_b = data[1]
        self._d_pool_b = data[2]

    def write_full_to_disk(self, file_path: Path):
        print("Saving")
        assert self._metadata_b is not None, "Metadata is not recorded in the replay."
        assert self._initial_game_state_b is not None, "Initial game state is not recorded in the replay."
        assert self._static_map_data_b is not None, "Static map data is not recorded in the replay."
        assert self._patch_graph_b is not None, "Patch graph metadat has not been read."
        assert self._d_pool_b is not None, "Data pool has not been read"

        data_chunks = [
            self._metadata_b,
            self._initial_game_state_b,
            self._static_map_data_b,
            self._patch_graph_b,
            self._d_pool_b
        ]

        # Partial compression for partial (metadata) reads.
        with open(file_path, 'wb') as f:
            for chunk in data_chunks:
                compressed = self.compressor(chunk)
                length = len(compressed)
                f.write(struct.pack('>I', length))
                f.write(compressed)

    def append_at_end(self, file_path: Path):
        pass #TODO

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

    def load_initial_game_state(self, game: ReplayInterface | None) -> GameState:
        if self._initial_game_state_b is None:
            raise ValueError("Initial game state is not recorded in the replay.")

        self.initial_game_state =  pickle.loads(self._initial_game_state_b)
        if game is not None:
            GameObject.set_game_recursive(self.initial_game_state, game)
        return self.initial_game_state

    def load_static_map_data(self, game: ReplayInterface) -> StaticMapData:
        if self._static_map_data_b is None:
            raise ValueError("Static map data is not recorded in the replay.")
        self.static_map_data = pickle.loads(self._static_map_data_b)
        GameObject.set_game_recursive(self.static_map_data, game)
        return self.static_map_data

    def load_path_tree(self):
        pass # TODO

    def load_patches(self, game: ReplayInterface) -> PatchGraph:
        pass # TODO

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
        pass # TODO

    def unload_patches(self):
        pass # TODO