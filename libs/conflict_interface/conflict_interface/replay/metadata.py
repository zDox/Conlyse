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


@dataclass
class TimelineMetadata:
    """
    Fixed-size per-replay timeline metadata header.

    Layout (little endian):
        - game_ended:   bool (stored as ?)
        - start_of_game: int32 (Unix seconds)
        - end_of_game:   int32 (Unix seconds, 0 if unknown)
        - game_id:       int32
        - player_id:     int32
        - scenario_id:   int32
        - day_of_game:   int32
        - speed:         int32 (game speed multiplier, e.g. 1, 2, 4)
        - segment_count: int32
    """

    _STRUCT_FORMAT = "<?iiiiiiii"
    size = struct.calcsize(_STRUCT_FORMAT)

    game_ended: bool
    start_of_game: int
    end_of_game: int
    game_id: int
    player_id: int
    scenario_id: int
    day_of_game: int
    speed: int
    segment_count: int

    def serialize(self) -> bytes:
        return struct.pack(
            self._STRUCT_FORMAT,
            self.game_ended,
            self.start_of_game,
            self.end_of_game,
            self.game_id,
            self.player_id,
            self.scenario_id,
            self.day_of_game,
            self.speed,
            self.segment_count,
        )

    @staticmethod
    def deserialize(data: bytes) -> "TimelineMetadata":
        (
            game_ended,
            start_of_game,
            end_of_game,
            game_id,
            player_id,
            scenario_id,
            day_of_game,
            speed,
            segment_count,
        ) = struct.unpack(TimelineMetadata._STRUCT_FORMAT, data)
        return TimelineMetadata(
            game_ended=game_ended,
            start_of_game=start_of_game,
            end_of_game=end_of_game,
            game_id=game_id,
            player_id=player_id,
            scenario_id=scenario_id,
            day_of_game=day_of_game,
            speed=speed,
            segment_count=segment_count,
        )
