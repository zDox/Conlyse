"""
Replay recording and playback system for game state changes.

This module provides the core Replay class for recording game state changes
over time and playing them back. Replays are stored in SQLite databases with
support for bidirectional time travel through patches.
"""
import os
from datetime import datetime
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

from conflict_interface.data_types.game_state.game_state import GameState
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.logger_config import get_logger
from conflict_interface.replay.constants import REPLAY_VERSION
from conflict_interface.replay.replay_cache import ReplayCache
from conflict_interface.replay.replay_database import ReplayDatabase
from conflict_interface.replay.replay_metadata import ReplayMetadata
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import ReplayPatch
from conflict_interface.replay.replay_validator import ReplayValidator
from conflict_interface.utils.helper import datetime_to_unix_ms
from conflict_interface.utils.helper import unix_ms_to_datetime

logger = get_logger()



class Replay:
    """
    Main replay class for recording and playing back game state changes.
    
    The Replay class manages a SQLite database that stores:
    - Game state snapshots at key timestamps
    - Patches representing changes between timestamps
    - Static map data
    - Action history
    
    Supports three modes:
    - 'r': Read-only mode for replay playback
    - 'w': Write mode for creating new replays
    - 'a': Append mode for adding to existing replays
    
    The replay system uses bidirectional patches for efficient time travel,
    allowing navigation both forward and backward through the game history
    without storing complete states at each timestamp.
    
    Attributes:
        filename: Path to the SQLite database file
        mode: Access mode ('r', 'w', or 'a')
        game_id: ID of the game being recorded/played
        player_id: ID of the player whose perspective is being recorded
    """

    def __init__(
        self,
        filename: str,
        mode: Literal['r', 'w', 'a'],
        game_id: int = None,
        player_id: int = None
    ):
        """
        Initialize a replay file.
        
        Args:
            filename: Path to the replay database file
            mode: 'r' for read, 'w' for write, 'a' for append
            game_id: Game ID (required for write/append modes)
            player_id: Player ID (required for write/append modes)
            
        Raises:
            ValueError: If mode is invalid
        """
        if mode not in ('r', 'w', 'a'):
            raise ValueError("Mode must be 'r' (read), 'w' (write), or 'a' (append)")

        self.filename = filename
        self.mode = mode
        self.game_id = game_id
        self.player_id = player_id
        self.db = ReplayDatabase()
        self.cache = ReplayCache()

        self._start_time: int = 0
        self._last_time: Optional[int] = None

        # In-memory lists of timestamps, are always loaded
        self._timestamps: List[int] = []
        self._game_state_timestamps: List[int] = []
        self._patch_timestamps: List[tuple[int, int]] = []

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        if self.mode == 'w':
            if self.game_id is None or self.player_id is None:
                raise ValueError("Game ID and Player ID must be provided in write mode")
        elif self.mode in ('r', 'a') and not os.path.exists(self.filename):
            raise FileNotFoundError(f"Replay file {self.filename} not found")

        self.db.connect(self.filename)
        if self.mode == 'w':
            self.db.create_tables()
            self.db.write_metadata(self.get_metadata())
        elif self.mode in ('r', 'a'):
            self.load_metadata_from_disk()
            self.load_game_state_timestamps()
            self.load_patch_timestamps()
        return self

    def close(self):
        """Close the replay file (alternative to using as context manager)."""
        self.db.disconnect()

    def load_metadata_from_disk(self):
        """
        Load replay metadata from disk.

        Returns:
            ReplayMetadata object containing metadata
        """
        metadata = self.db.read_metadata()
        self.game_id = metadata.game_id
        self.player_id = metadata.player_id
        self._start_time = metadata.start_time
        self._last_time = metadata.last_time

    def get_metadata(self) -> ReplayMetadata:
        """
        Get replay metadata.

        Returns:
            ReplayMetadata object containing metadata
        """
        return ReplayMetadata(
            version=REPLAY_VERSION,
            game_id=self.game_id,
            player_id=self.player_id,
            start_time=self._start_time,
            last_time=self._last_time
        )

    def load_game_state_timestamps(self):
        # Load game state timestamps (but not the states themselves)
        self._game_state_timestamps = self.db.read_game_state_timestamps()
        self._game_state_timestamps.sort()

    def load_patch_timestamps(self):
        # Load patch timestamps (but not the patches themselves)
        for (from_ts, to_ts) in self.db.read_patch_timestamps():
            self._patch_timestamps.append((from_ts, to_ts))
            if to_ts not in self._timestamps:
                self._timestamps.append(to_ts)
        self._timestamps.sort()

    def load_patches_and_patch_timestamps(self):
        """
        Load patches and timestamps into memory for fast access.
        """
        for (from_ts, to_ts), patch in self.db.read_patches().items():
            self.cache.add_patch((from_ts, to_ts), patch)
            self._patch_timestamps.append((from_ts, to_ts))
            if to_ts not in self._timestamps:
                self._timestamps.append(to_ts)
        self._timestamps.sort()

    def load_patches_from_disk_into_cache(self):
        """
        Load all patches from disk into the in-memory cache.
        """
        for (from_ts, to_ts), patch in self.db.read_patches().items():
            self.cache.add_patch((from_ts, to_ts), patch)

    @property
    def start_time(self) -> Optional[datetime]:
        """
        Get the replay start time as a datetime object.
        
        Returns:
            The start time in UTC, or None if not set
        """
        return unix_ms_to_datetime(self._start_time)

    @property
    def last_time(self) -> Optional[datetime]:
        """
        Get the last recorded time as a datetime object.
        
        Returns:
            The last recorded time in UTC, or None if not set
        """
        return unix_ms_to_datetime(self._last_time)

    def _find_patch_path(self, start: int, target: int) -> List[ReplayPatch]:
        """
        Calculate the sequence of patches needed to jump between timestamps.
        
        This method finds the optimal path through the patch graph to move from
        the start timestamp to the target timestamp. It supports both forward
        and backward time travel.
        
        Args:
            start: Starting timestamp in milliseconds
            target: Target timestamp in milliseconds
            
        Returns:
            List of patches to apply in sequence
            
        Raises:
            IOError: If replay is not in read or append mode
            ValueError: If target is before the replay start time
        """
        if self.mode not in ('r', 'a'):
            raise IOError("Replay must be in read or append mode to jump")
        if target < self._start_time:
            raise ValueError(f"Cannot jump to {target} before start time {self._start_time}")

        patches = []
        current = start

        # Forward time travel: Find patches that move us closer to target
        if target > start:
            while current < target:
                next_patch = None
                # Search for a patch that starts at current and ends before or at target
                for from_ts, to_ts in self._patch_timestamps:
                    if from_ts == current and from_ts < to_ts <= target:
                        next_patch = (to_ts, self.get_patch(from_ts, to_ts))
                        break
                if not next_patch:
                    break  # No more patches available, stop here
                current, patch = next_patch
                patches.append(patch)

        # Backward time travel: Find patches that move us back toward target
        elif target < start:
            while current > target:
                next_patch = None
                # Search for a backward patch that starts at current and ends at or after target
                for (from_ts, to_ts), patch in self._patch_timestamps:
                    if from_ts == current and from_ts > to_ts >= target:
                        next_patch = (to_ts, self.get_patch(from_ts, to_ts))
                        break
                if not next_patch:
                    break  # No more patches available, stop here
                current, patch = next_patch
                patches.append(patch)

        return patches

    def find_patch_path(self, start: datetime, target: datetime) -> Tuple[List[ReplayPatch], datetime]:
        """
        Jump between two datetimes, snapping to nearest available timestamps.
        
        Args:
            start: Starting datetime
            target: Target datetime
            
        Returns:
            Tuple of (list of patches to apply, actual target datetime reached)
        """
        start_ms = datetime_to_unix_ms(start)
        target_ms = datetime_to_unix_ms(target)

        # Snap to nearest available timestamps
        start_ms = max([ts for ts in self._timestamps + [self._start_time] if ts <= start_ms], default=self._start_time)
        target_ms = max([ts for ts in self._timestamps if ts <= target_ms], default=self._start_time)

        return self._find_patch_path(start_ms, target_ms), unix_ms_to_datetime(target_ms)

    def get_patch(self, from_timestamp: int, to_timestamp: int) -> ReplayPatch:
        """
        Retrieve a specific patch from memory.
        
        Args:
            from_timestamp: Starting timestamp
            to_timestamp: Ending timestamp
            
        Returns:
            The requested ReplayPatch
            
        Raises:
            Exception: If the patch is not found
        """
        if self.cache.has_patch((from_timestamp, to_timestamp)):
            # Patch already loaded in memory
            patch = self.cache.get_patch((from_timestamp, to_timestamp))
            return patch
        patch = self.db.read_patch(from_timestamp, to_timestamp)
        if patch is None:
            raise Exception(f"Patch not found from {from_timestamp} to {to_timestamp}")
        self.cache.add_patch((from_timestamp, to_timestamp), patch)
        return patch

    def get_timestamps(self) -> List[int]:
        """
        Get all timestamps where patches exist.
        
        Returns:
            Sorted list of timestamps in milliseconds (direct reference, do not modify)
        """
        return self._timestamps

    def get_game_state_timestamps(self) -> List[int]:
        """
        Get all timestamps where complete game states are stored.
        
        Returns:
            Sorted list of timestamps in milliseconds (direct reference, do not modify)
        """
        return self._game_state_timestamps

    def record_bipatch(
        self,
        time_stamp: datetime,
        game_id: int,
        player_id: int,
        replay_patch: BidirectionalReplayPatch
    ):
        """
        Record a bidirectional patch at a specific timestamp.
        
        Stores both forward and backward patches for efficient time travel.
        
        Args:
            time_stamp: When this patch was created
            game_id: Game ID (must match replay's game_id)
            player_id: Player ID (must match replay's player_id or be 0)
            replay_patch: The bidirectional patch to record
            
        Raises:
            IOError: If replay is not in write or append mode
            CorruptReplay: If game/player ID mismatch or timestamp out of order
        """
        time_stamp_ms = Replay.datetime_to_ms(time_stamp)
        ReplayValidator.validate_write_mode(self.mode)
        ReplayValidator.validate_game_player_ids(self.get_metadata(), game_id, player_id)
        ReplayValidator.validate_timestamp_order(self.get_metadata(), time_stamp_ms)

        self._timestamps.append(time_stamp_ms)
        forward_ts = (self._last_time or self._start_time, time_stamp_ms)
        backward_ts = (time_stamp_ms, self._last_time or self._start_time)
        self.db.write_patch(forward_ts[0], forward_ts[1], replay_patch.forward_patch.to_bytes())
        self.db.write_patch(backward_ts[0], backward_ts[1], replay_patch.backward_patch.to_bytes())

        self._last_time = time_stamp_ms
        self.db.write_metadata(self.get_metadata())

    def record_initial_game_state(self, time_stamp: datetime, game_id: int, player_id: int, game_state: GameState):
        """
        Record the initial game state snapshot.
        
        This should be the first call when creating a new replay.
        
        Args:
            time_stamp: When the game state was captured
            game_id: Game ID (must match replay's game_id)
            player_id: Player ID (must match replay's player_id or be 0)
            game_state: Complete game state dictionary
            
        Raises:
            IOError: If replay is not in write or append mode
            CorruptReplay: If game/player ID mismatch or timestamp out of order
        """
        time_stamp_ms = Replay.datetime_to_ms(time_stamp)

        ReplayValidator.validate_write_mode(self.mode)
        ReplayValidator.validate_game_player_ids(self.get_metadata(), game_id, player_id)
        ReplayValidator.validate_timestamp_order(self.get_metadata(), time_stamp_ms)

        self.db.write_game_state(time_stamp_ms, game_state)
        self._game_state_timestamps.append(time_stamp_ms)
        self._game_state_timestamps.sort()
        self._start_time = time_stamp_ms
        self._last_time = time_stamp_ms
        self.db.write_metadata(self.get_metadata())

    def record_static_map_data(self, static_map_data: StaticMapData, game_id: int, player_id: int):
        """
        Record static map data that doesn't change during the game.
        
        Args:
            static_map_data: Dictionary containing static map information
            game_id: Game ID (must match replay's game_id)
            player_id: Player ID (must match replay's player_id or be 0)
            
        Raises:
            IOError: If replay is not in write or append mode
            CorruptReplay: If game/player ID mismatch
        """
        ReplayValidator.validate_write_mode(self.mode)
        ReplayValidator.validate_game_player_ids(self.get_metadata(), game_id, player_id)
        self.db.write_static_map_data(static_map_data)

    def load_static_map_data(self) -> StaticMapData:
        """
        Load static map data from disk.
        The Loaded GameObject has no reference to any GameInterface.

        Returns:
            The static map data dictionary
        """
        return self.db.read_static_map_data()

    def load_initial_game_state(self) -> GameState:
        """
        Loads the initial game state from disk and returns it.
        It does not cache the game state in memory.
        The Loaded Game_state has no reference to the GameInterface.
        
        Returns:
            The game state dictionary from the start of the replay
        """
        return self.db.read_game_state(self._start_time)


    def check_integrity(self) -> bool:
        time_stamps = self.get_timestamps()
        current_ts = self.start_time
        error_detected = False
        for next_ts in time_stamps:
            try:
                self._find_patch_path(current_ts, next_ts)
            except Exception as e:
                logger.error(f"Integrity check failed jumping Forwards from {current_ts} to {next_ts}: {e}")
                error_detected = True
            current_ts = next_ts

        current_ts = self.last_time
        time_stamps = list(reversed(time_stamps))
        for next_ts in time_stamps:
            try:
                self._find_patch_path(current_ts, next_ts)
            except Exception as e:
                logger.error(f"Integrity check failed jumping Backwards from {current_ts} to {next_ts}: {e}")
                error_detected = True
            current_ts = next_ts

        return error_detected


