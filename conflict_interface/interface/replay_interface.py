from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Callable
from typing import override

from tqdm import tqdm

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.hook_system.replay_hook import ReplayHook
from conflict_interface.hook_system.replay_hook_system import ReplayHookSystem
from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.replay.patch_graph_node import PatchGraphNode
from conflict_interface.replay.replay import Replay
import bisect

logger = get_logger()

class ReplayInterface(GameInterface):
    def __init__(self, file_path: Path | str):
        super().__init__()
        self.file_path = Path(file_path)
        self.replay = Replay(self.file_path, 'r')
        self._hook_system = ReplayHookSystem()
        self.game_state: GameState | None = None
        self.static_map_data = None
        self.player_id: int | None = None
        self.current_time: datetime | None = None
        self.game_id: int | None = None
        self.last_patch_time = None
        self._time_stamps_cache = None
        self.current_timestamp_index: int = 0

    def open(self):
        steps = [
            "Opening replay",
            "Loading initial game state",
            "Parsing timestamps",
            "Loading static map data",
            "Finalizing setup",
        ]

        pbar = tqdm(total=len(steps), desc="Loading Replay", unit="step")

        # Step 1: open replay
        self.replay.open()
        pbar.set_description(steps[0])
        pbar.update(1)

        # Step 2: load game state
        self.game_state = self.replay.load_initial_game_state()
        self.game_state.set_game(self)
        pbar.set_description(steps[1])
        pbar.update(1)

        # Step 3: parse timestamps
        _raw = self.replay.storage.patch_graph.time_stamps_cache
        self._time_stamps_cache = [
            datetime.fromtimestamp(ts, tz=UTC) for ts in _raw
        ]
        pbar.set_description(steps[2])
        pbar.update(1)

        # Step 4: static map data
        self.static_map_data = self.replay.load_static_map_data()
        self.static_map_data.set_game(self)
        self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)
        pbar.set_description(steps[3])
        pbar.update(1)

        # Step 5: final metadata
        self._update_player_id()
        self.game_id = self.replay.game_id
        self.current_time = self.replay.get_start_time()
        self.last_patch_time = self.current_time
        pbar.set_description(steps[4])
        pbar.update(1)

        pbar.close()


    def close(self):
        self.replay.close()

    def _find_current_player_id(self) -> int | None:
        for player in self.get_players().values():
            if (
                    player.activity_state == "ACTIVE" or
                    player.activity_state == "UNKNOWN" or
                    player.activity_state == "INACTIVE"or
                    player.activity_state == "ABANDONED"
            ):

                return player.player_id

    def _update_player_id(self):
        if self.player_id is not None and (
                self.get_player(self.player_id).activity_state == "ACTIVE" or
                self.get_player(self.player_id).activity_state == "UNKNOWN" or
                self.get_player(self.player_id).activity_state == "INACTIVE" or
                self.get_player(self.player_id).activity_state == "ABANDONED"
        ):
            return

        self.player_id = self._find_current_player_id()

        if self.player_id is None:
            raise Exception("Could not determine player ID")

    @override
    def client_time(self) -> datetime:
        return self.current_time

    @property
    def start_time(self) -> datetime:
        return self.replay.get_start_time()

    @property
    def end_time(self) -> datetime:
        return self.replay.get_last_time()

    def jump_to(self, time_stamp: datetime) -> list[PatchGraphNode]:
        """
        Jumps to the specified timestamp in the replay.

        Returns applied patches
        """
        if self.current_time == time_stamp:
            return []
        if time_stamp < self.replay.get_start_time() == self.current_time:
            return []

        if time_stamp < self.replay.get_start_time():
            self.game_state = self.replay.load_initial_game_state()
            self.game_state.set_game(self)
            return []

        patches = self.replay.storage.patch_graph.find_patch_path(self.last_patch_time, time_stamp)
        self._apply_patches_and_update_state(patches, time_stamp)

        # Update the current timestamp index for O(1) next/previous operations
        self.current_timestamp_index = bisect.bisect_left(self._time_stamps_cache, time_stamp)

        return patches

    def _apply_patches_and_update_state(self, patches, target_time: datetime) -> None:
        """
        Helper method to apply patches and update game state.
        Reduces code duplication across jump methods.
        """
        for patch in patches:
            self.replay.apply_patch(patch, self.game_state, self)

        self.current_time = target_time
        self.last_patch_time = target_time
        #self.game_state.states.map_state.map.set_static_map_data(self.static_map_data)
        self._update_player_id()

        if hasattr(self, '_hook_system'):
            self._hook_system.execute_que()

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

        patches = self.replay.storage.patch_graph.find_patch_path(self.current_time, next_timestamp)

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
        previous_timestamp = self.get_previous_timestamp()

        if previous_timestamp is None or previous_timestamp < self.replay.get_start_time():
            return False

        # Need to reload and replay from start since patches can't be unapplied
        self.game_state = self.replay.load_initial_game_state()
        self.game_state.set_game(self)

        patches, _ = self.replay.storage.patch_graph.find_patch_path(self.replay.get_start_time(), previous_timestamp)
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


    """
    Hook System Events
    """


    def on_province_attribute_change(self, callback: Callable, attributes: list[str]) -> None:
        """
        Register a callback for when an attribute of a province changes.

        The callback will be called with the province object:
        callback(province, old_value, new_value)
        where province is the Province object whose attribute changed,
        old_value is the previous attribute value, and
        where new_value is the new attribute value.

        Args:
            callback: Function to call when the province attribute changes
            attributes: The name of the attributes to watch (e.g., "owner_id")
        """
        path = ["states", "map_state","map","locations"]
        path_idx = self.replay.storage.path_tree.old_path_to_idx(path)

        def wrapper(path, reference, changed_data):
            callback(reference, changed_data)

        hook = ReplayHook( callback = wrapper,
                           change_types = [ADD_OPERATION, REPLACE_OPERATION, REMOVE_OPERATION],
                           attributes = attributes,
                           path = path_idx
                           )
        self._hook_system.register(hook)