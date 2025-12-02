import struct
from dataclasses import dataclass



@dataclass
class Metadata:
    start_time: int
    last_time: int
    max_patches: int
    current_patches: int
    patch_index_start: int

    def serialize(self) -> bytes:
        return struct.pack(">iiiii",
                           self.start_time,
                           self.last_time,
                           self.max_patches,
                           self.current_patches,
                           self.patch_index_start)

    @staticmethod
    def deserialize(data: bytes) -> 'Metadata':
        start_time, last_time, max_patches, current_patches, patch_index_start = struct.unpack(">iiiii", data)
        return Metadata(start_time, last_time, max_patches, current_patches, patch_index_start)

