import bisect
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Literal
from typing import override

from conflict_interface.hook_system.replay_hook_system import ReplayHookSystem
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay import Replay

logger = get_logger()

class ReplayInterface(GameInterface):
    def __init__(self, file_path: Path | str, player_id: int | None = None, game_id: int | None = None):
        super().__init__()
        self.current_time: datetime | None = None
        self.current_timestamp_index: int = 0
        self.player_id: int | None = player_id
        self.game_id: int | None = game_id

        self._time_stamps_cache = None
        self._file_path: Path = Path(file_path)
        self._replay: Replay | None = None
        self._hook_system: ReplayHookSystem | None = None

        self._mode: Literal['w', 'r', 'a', 'rw'] | None = None
        self._is_open: bool = False



    def open(self, mode: Literal['w', 'r', 'a', 'rw'], max_patches: int | None = None) -> bool:
        # Auto close if already open
        if self._is_open:
            self.close()

        self._mode = mode

        logger.debug("Creating Replay")
        if self._mode in ['w', 'rw'] and max_patches is None:
            logger.warning("Max Patches was not set. Returning")
            return False

        self._replay = Replay(file_path=self._file_path, mode = self._mode, player_id=self.player_id, game_id=self.game_id, max_patches=max_patches)
        self._replay.open()

        if self._mode == 'a':
            self._is_open = True
            logger.debug("Initialization Completed Successfully")
            return True

        self._hook_system = ReplayHookSystem(self._replay)

        self.game_state = self._replay.storage.initial_game_state
        self.game_state.states.map_state.map.set_static_map_data(self._replay.storage.static_map_data)

        logger.debug("Parsing TimeStamps for the Cache")
        _raw = self._replay.storage.patch_graph.time_stamps_cache
        self._time_stamps_cache = [
            datetime.fromtimestamp(ts, tz=UTC) for ts in _raw
        ]

        # Step 5: final metadata
        self._update_player_id()
        self.current_time = self._replay.get_start_time()

        self._is_open = True
        logger.debug("Initialization Completed Successfully")
        return True


    def close(self):
        if not self._is_open:
            logger.warning("Tried to close replay that was not open!")
            return

        assert self._replay is not None, "Replay is None"

        if self._mode == 'w' or self._mode == 'rw':
            logger.debug("Jumping to Last state for proper closing")
            self.jump_to(self._replay.get_last_time())
            self._replay.set_last_game_state(self.game_state)

        self._replay.close()

    def _update_player_id(self):
        valid_states = {"ACTIVE", "UNKNOWN", "INACTIVE", "ABANDONED"}

        # If current player_id exists and is valid, nothing to do
        if self.player_id is not None:
            player = self.get_player(self.player_id)
            if player.activity_state in valid_states:
                return

        # Otherwise, find any player with a valid state
        for player in self.get_players().values():
            if player.activity_state in valid_states:
                self.player_id = player.player_id
                self._replay.player_id = self.player_id
                return

        # No valid player found
        raise Exception("Could not determine player ID")

    @override
    def client_time(self) -> datetime:
        return self.current_time

    @property
    def start_time(self) -> datetime:
        return self._replay.get_start_time()

    @property
    def end_time(self) -> datetime:
        return self._replay.get_last_time()

    def jump_to(self, time_stamp: datetime) -> None:
        """
        Jumps to the specified timestamp in the replay.

        Returns applied patches
        """
        if self.current_time == time_stamp:
            return
        if time_stamp < self._replay.get_start_time() == self.current_time:
            return

        if time_stamp < self._replay.get_start_time():
            self.game_state = self._replay.storage.initial_game_state
            self.game_state.set_game(self)
            return

        patches = self._replay.storage.patch_graph.find_patch_path(self._replay.get_last_time(), time_stamp)
        self._apply_patches_and_update_state(patches, time_stamp)

        # Update the current timestamp index for O(1) next/previous operations
        self.current_timestamp_index = bisect.bisect_left(self._time_stamps_cache, time_stamp)

        # DEBUG ----------------
        #return patches
        # ----------------------

    def _apply_patches_and_update_state(self, patches, target_time: datetime) -> None:
        """
        Helper method to apply patches and update game state.
        Reduces code duplication across jump methods.
        """
        for patch in patches:
            self._replay.apply_patch(patch, self.game_state, self)

        self.current_time = target_time
        self.last_patch_time = target_time
        #self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)
        self._update_player_id()

        if hasattr(self, '_hook_system'):
            self._hook_system.execute_queue()

    def jump_to_next_patch(self) -> bool:
        """
        Jumps to the next patch in the replay.
        Optimized for O(1) sequential forward traversal.

        Returns:
            True if successfully jumped to next patch, False if at end of replay.
        """
        next_timestamp = self.get_next_timestamp()

        if next_timestamp is None:
            return False

        patches = self._replay.storage.patch_graph.find_patch_path(self.current_time, next_timestamp)

        if patches:
            self._apply_patches_and_update_state(patches, next_timestamp)
            self.current_timestamp_index += 1

        return True

    def jump_to_previous_patch(self) -> bool:
        """
        Jumps to the previous patch in the replay.
        Requires reloading from initial state and applying patches up to target.

        Returns:
            True if successfully jumped to previous patch, False if at start of replay.
        """
        # TODO
        previous_timestamp = self.get_previous_timestamp()

        if previous_timestamp is None or previous_timestamp < self._replay.get_start_time():
            return False

        # Need to reload and replay from start since patches can't be unapplied
        self.game_state = self._replay.storage.initial_game_state
        self.game_state.set_game(self)

        patches, _ = self._replay.storage.patch_graph.find_patch_path(self._replay.get_start_time(), previous_timestamp)
        self._apply_patches_and_update_state(patches, previous_timestamp)
        self.current_timestamp_index -= 1

        return True

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


    """
    Hook System
    """


    def get_hook_system(self) -> ReplayHookSystem:
        return self._hook_system

    def unregister_all_hooks(self):
        self.get_hook_system().unregister_all_hooks()