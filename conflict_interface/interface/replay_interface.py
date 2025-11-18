from datetime import UTC
from datetime import datetime
from datetime import timedelta
from time import time
from typing import override

from conflict_interface.data_types.game_object import parse_any
from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.apply_replay import apply_patch_any
from conflict_interface.replay.replay import Replay
import bisect

logger = get_logger()

class ReplayInterface(GameInterface):
    def __init__(self, filename: str):
        super().__init__()
        self.replay = Replay(filename, 'r')
        self.game_state: GameState | None = None
        self.static_map_data = None
        self.player_id: int | None = None
        self.current_time: datetime | None = None
        self.game_id: int | None = None
        self.last_patch_time = None
        self._time_stamps_cache = None  # Cache for converted datetime timestamps
        self._raw_timestamps_ref = None  # Reference to replay's timestamp list
        self.current_timestamp_index: int = 0

    def open(self):
        t1 = time()
        self.replay.open()
        logger.debug(f"Loading Game State from disk took {time() - t1} seconds")
        t2 = time()
        self.game_state = self.replay.load_initial_game_state()
        self.game_state.set_game(self)
        logger.debug(f"GameState parse took {time() - t2} seconds")
        t3 = time()
        self.static_map_data = self.replay.load_static_map_data()
        self.static_map_data.set_game(self)
        self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)
        self._update_player_id()
        self.game_id = self.replay.game_id
        self.current_time = self.replay.start_time
        self.last_patch_time = self.replay.start_time

        # Store reference to replay's timestamps and convert once
        self._raw_timestamps_ref = self.replay.get_timestamps()
        self._time_stamps_cache = [datetime.fromtimestamp(ts / 1000, tz=UTC) for ts in self._raw_timestamps_ref]

        logger.debug(f"Loading and setting static map data took {time() - t3} seconds")

    def close(self):
        self.replay.close()

    def _find_current_player_id(self) -> int | None:
        for player in self.get_players().values():
            if player.activity_state == "ACTIVE" or player.activity_state == "UNKNOWN":
                return player.player_id

    def _update_player_id(self):
        if self.player_id is not None and (self.get_player(self.player_id).activity_state == "ACTIVE"
            or self.get_player(self.player_id).activity_state == "UNKNOWN"):
            return

        self.player_id = self._find_current_player_id()

        if self.player_id is None:
            raise Exception("Could not determine player ID")

    @override
    def client_time(self) -> datetime:
        return self.current_time

    @property
    def start_time(self) -> datetime:
        return self.replay.start_time

    @property
    def end_time(self) -> datetime:
        return self.replay.last_time

    def jump_to(self, time_stamp: datetime) -> None:
        """
        Jumps to the specified timestamp in the replay.
        """
        if self.current_time == time_stamp:
            return
        if time_stamp < self.replay.start_time == self.current_time:
            return

        if time_stamp < self.replay.start_time:
            self.game_state = self.replay.load_initial_game_state()
            self.game_state.set_game(self)

            return

        patches, self.last_patch_time = self.replay.find_patch_path(self.last_patch_time, time_stamp)
        for rp in patches:
            apply_patch_any(rp, self.game_state, self)

        self.current_time = time_stamp

        # Update the current timestamp index for O(1) next/previous operations
        self.current_timestamp_index = bisect.bisect_left(self._time_stamps_cache, time_stamp)

        self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)
        self._update_player_id()

    def get_timestamps(self) -> list[datetime]:
        """
        Get all timestamps in the replay as datetime objects.

        Returns:
            Cached list of datetime timestamps (O(1) operation)
        """
        return self._time_stamps_cache

    def get_next_timestamp(self, timestamp = None) -> datetime | None:
        """
        Gets the next timestamp after the given timestamp.
        O(1) when timestamp is None, O(log n) when a specific timestamp is provided.
        """
        ts = self._time_stamps_cache

        if timestamp is None:
            # Use cached index for O(1) lookup
            next_idx = self.current_timestamp_index + 1
            return ts[next_idx] if next_idx < len(ts) else None

        # Fallback for custom timestamp (O(log n))
        i = bisect.bisect_right(ts, timestamp)
        return ts[i] if i < len(ts) else None

    def get_previous_timestamp(self, timestamp = None) -> datetime | None:
        """
        Gets the previous timestamp before the given timestamp.
        O(1) when timestamp is None, O(log n) when a specific timestamp is provided.
        """
        ts = self._time_stamps_cache

        if timestamp is None:
            # Use cached index for O(1) lookup
            prev_idx = self.current_timestamp_index - 1
            return ts[prev_idx] if prev_idx >= 0 else None

        # Fallback for custom timestamp (O(log n))
        i = bisect.bisect_left(ts, timestamp)
        return ts[i - 1] if i > 0 else None

    def average_update_frequency(self) -> timedelta:
        """
        Computes the average update frequency as a timedelta.
        """
        timestamps = self.get_timestamps()
        if len(timestamps) < 2:  # Need at least 2 timestamps to calculate frequency
            return timedelta(0)

        total_time = (self.end_time - self.end_time).total_seconds()
        num_intervals = len(timestamps) - 1

        return timedelta(seconds=num_intervals / total_time if total_time > 0 else 0.0)
