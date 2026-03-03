import struct
from dataclasses import dataclass



@dataclass
class Metadata:
    """
    Fixed-size replay metadata header.

    Layout (little endian):
        - start_time:        int32
        - last_time:         int32
        - max_patches:       int32
        - current_patches:   int32
        - patch_index_start: int32
        - is_fragmented:     bool (stored as ?)
        - map_id:            40-byte UTF-8 string (padded with null bytes)
    """

    _STRUCT_FORMAT = "<iiiii?40s"
    size = struct.calcsize(_STRUCT_FORMAT)

    start_time: int
    last_time: int
    max_patches: int
    current_patches: int
    patch_index_start: int
    is_fragmented: bool
    map_id: str = ""

    def serialize(self) -> bytes:
        # Encode map_id as fixed-width 40-byte UTF-8 string, padded with nulls.
        map_id_bytes = self.map_id.encode("utf-8")[:40]
        map_id_bytes = map_id_bytes.ljust(40, b"\x00")

        return struct.pack(
            self._STRUCT_FORMAT,
            self.start_time,
            self.last_time,
            self.max_patches,
            self.current_patches,
            self.patch_index_start,
            self.is_fragmented,
            map_id_bytes,
        )

    @staticmethod
    def deserialize(data: bytes) -> 'Metadata':
        start_time, last_time, max_patches, current_patches, patch_index_start, is_fragmented, map_id_bytes = struct.unpack(
            Metadata._STRUCT_FORMAT, data
        )
        # Decode map_id, stripping trailing null bytes.
        map_id = map_id_bytes.rstrip(b"\x00").decode("utf-8")
        return Metadata(
            start_time=start_time,
            last_time=last_time,
            max_patches=max_patches,
            current_patches=current_patches,
            patch_index_start=patch_index_start,
            is_fragmented=is_fragmented,
            map_id=map_id,
        )

