import os
import pickle
import struct

import lz4.frame

from conflict_interface.replayv2.metadata import Metadata
from conflict_interface.replayv2.patch_graph import PatchGraph
from conflict_interface.replayv2.path_tree import PathTree


class ReplayStorage:
    def __init__(self):
        self.metadata: Metadata | None = None
        self.initial_game_state: bytes | None = None
        self.static_map_data: bytes | None = None
        self.path_tree: PathTree | None = None
        self.patch_graph: PatchGraph | None = None

        self.compressor = lz4.frame.compress
        self.decompressor = lz4.frame.decompress

    def parse_data(self, data):
        self.metadata = pickle.loads(data[0])
        self.initial_game_state = data[1]
        self.static_map_data = data[2]
        self.path_tree = pickle.loads(data[3])
        self.patch_graph = pickle.loads(data[4])

    def load_full_from_disk(self, file_path: str):
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

        self.parse_data(data)

    def safe_to_disk(self, file_path: str):
        data_chunks = \
            [
                pickle.dumps(self.metadata),
                pickle.dumps(self.initial_game_state),
                pickle.dumps(self.static_map_data),
                pickle.dumps(self.path_tree),
                pickle.dumps(self.patch_graph)
            ]

        self.write_to_file(data_chunks, file_path)

    def write_to_file(self, data_chunks, file_path: str):
        # Partial compression for partial (metadata) reads.
        with open(file_path, 'wb') as f:
            for chunk in data_chunks:
                compressed = self.compressor(chunk)
                length = len(compressed)
                f.write(struct.pack('>I', length))
                f.write(compressed)

    def create_new_file(self, file_path: str):
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

