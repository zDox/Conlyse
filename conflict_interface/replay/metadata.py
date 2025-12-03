import struct
from dataclasses import dataclass



@dataclass
class Metadata:
    size = 21
    start_time: int
    last_time: int
    max_patches: int
    current_patches: int
    patch_index_start: int
    is_fragmented: bool

    def serialize(self) -> bytes:
        return struct.pack("<iiiii?",
                           self.start_time,
                           self.last_time,
                           self. max_patches,
                           self.current_patches,
                           self.patch_index_start,
                           self.is_fragmented)

    @staticmethod
    def deserialize(data: bytes) -> 'Metadata':
        start_time, last_time, max_patches, current_patches, patch_index_start, is_fragmented = struct.unpack("<iiiii?", data)
        return Metadata(start_time, last_time, max_patches, current_patches, patch_index_start, is_fragmented)

