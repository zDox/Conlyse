import struct
from dataclasses import dataclass


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
