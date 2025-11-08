"""
Replay recording and playback system for game state changes.

This module provides the core Replay class for recording game state changes
over time and playing them back. Replays are stored in SQLite databases with
support for bidirectional time travel through patches.
"""
import json
import sqlite3
import os
import zlib
from datetime import UTC, datetime
from sqlite3 import Connection
from typing import Literal, Dict, List, Optional
from typing import Tuple

from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch, ReplayPatch

logger = get_logger()


class CorruptReplay(Exception):
    """Raised when a replay file is corrupted or has an invalid format."""
    pass


# Replay file format version
VERSION = 3

# Required keys in the information table
MANDATORY_KEYS = ["version", "game_id", "player_id", "start_time"]

# Database table names
TABLE_INFORMATION = "information"
TABLE_GAME_STATE = "game_state"
TABLE_PATCHES = "patches"
TABLE_ACTIONS = "actions"
TABLE_STATIC_MAP_DATA = "static_map_data"

# Information table primary key
INFO_TABLE_PK = 1

# Timestamp conversion factor (milliseconds per second)
MS_PER_SECOND = 1000


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
        conn: SQLite database connection
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
        self.conn: Optional[Connection] = None

        self._start_time: int = 0
        self._last_time: Optional[int] = None

        # In-memory caches (only patches and timestamps, no game states)
        self._patches: Dict[tuple[int, int], ReplayPatch] = {}  # (from_ts, to_ts) -> patch
        self._timestamps: List[int] = []
        self._game_state_timestamps: List[int] = []
        self._static_map_data: Optional[dict] = None

    def __enter__(self):
        """
        Context manager entry - opens the database connection.
        
        Returns:
            self for use in with statements
            
        Raises:
            ValueError: If game_id or player_id missing in write mode
            FileNotFoundError: If file doesn't exist in read/append mode
        """
        if self.mode == 'w':
            if self.game_id is None or self.player_id is None:
                raise ValueError("Game ID and Player ID must be provided in write mode")
        elif self.mode in ('r', 'a') and not os.path.exists(self.filename):
            raise FileNotFoundError(f"Replay file {self.filename} not found")

        self.conn = sqlite3.connect(self.filename)
        if self.mode == 'w':
            self._create_tables()
            self._write_information()
        elif self.mode in ('r', 'a'):
            self._load_information()
            self._load_into_memory()  # Load patches and timestamps, not game states
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def open(self):
        """Open the replay file (alternative to using as context manager)."""
        self.__enter__()

    def close(self):
        """Close the replay file (alternative to using as context manager)."""
        self.__exit__(None, None, None)

    def _load_into_memory(self):
        """
        Load patches and timestamps into memory for fast access.
        
        Game states are kept on disk and loaded on demand to reduce memory usage.
        This method loads:
        - Timestamps of all game state snapshots
        - All patches for time travel
        - Static map data
        """
        # Load game state timestamps (but not the states themselves)
        cursor = self.conn.execute(f"SELECT timestamp FROM {TABLE_GAME_STATE}")
        self._game_state_timestamps = [row[0] for row in cursor.fetchall()]
        self._game_state_timestamps.sort()

        # Load patches
        cursor = self.conn.execute(f"SELECT from_timestamp, to_timestamp, patch FROM {TABLE_PATCHES}")
        for from_ts, to_ts, patch_str in cursor.fetchall():
            self._patches[(from_ts, to_ts)] = ReplayPatch.from_string(patch_str)
            if to_ts not in self._timestamps:
                self._timestamps.append(to_ts)
        self._timestamps.sort()

        # Load static map data
        cursor = self.conn.execute(f"SELECT data FROM {TABLE_STATIC_MAP_DATA}")
        if static_data := cursor.fetchone():
            self._static_map_data = json.loads(zlib.decompress(static_data[0]).decode('utf-8'))

    def _create_tables(self):
        """Create SQLite database schema for replay storage."""
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_INFORMATION} (
                id INTEGER PRIMARY KEY,
                version INTEGER,
                game_id INTEGER,
                player_id INTEGER,
                start_time INTEGER,
                last_time INTEGER
            )
        """)
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_GAME_STATE} (
                timestamp INTEGER PRIMARY KEY,
                data BLOB
            )
        """)
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_PATCHES} (
                from_timestamp INTEGER,
                to_timestamp INTEGER,
                patch TEXT
            )
        """)
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_ACTIONS} (
                timestamp INTEGER PRIMARY KEY,
                action TEXT
            )
        """)
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_STATIC_MAP_DATA} (
                data BLOB
            )
        """)
        self.conn.commit()

    @property
    def start_time(self) -> Optional[datetime]:
        """
        Get the replay start time as a datetime object.
        
        Returns:
            The start time in UTC, or None if not set
        """
        return datetime.fromtimestamp(self._start_time / MS_PER_SECOND, tz=UTC) if self._start_time else None

    @property
    def last_time(self) -> Optional[datetime]:
        """
        Get the last recorded time as a datetime object.
        
        Returns:
            The last recorded time in UTC, or None if not set
        """
        return datetime.fromtimestamp(self._last_time / MS_PER_SECOND, tz=UTC) if self._last_time else None

    def _write_information(self):
        """Write or update replay metadata in the information table."""
        self.conn.execute(f"""
            INSERT OR REPLACE INTO {TABLE_INFORMATION} (id, version, game_id, player_id, start_time, last_time) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (INFO_TABLE_PK, VERSION, self.game_id, self.player_id, self._start_time, self._last_time))
        self.conn.commit()

    def _load_information(self):
        """
        Load replay metadata from the information table.
        
        Raises:
            CorruptReplay: If information table is empty or version mismatch
        """
        cursor = self.conn.execute(
            f"SELECT version, game_id, player_id, start_time, last_time FROM {TABLE_INFORMATION} WHERE id = ?", 
            (INFO_TABLE_PK,))
        row = cursor.fetchone()
        if not row:
            raise CorruptReplay("Information table is empty")
        version, self.game_id, self.player_id, self._start_time, self._last_time = row
        if version != VERSION:
            raise CorruptReplay(f"Unsupported version {version}")

    def _validate_write_mode(self):
        """
        Validate that replay is in write or append mode.
        
        Raises:
            IOError: If replay is not in write or append mode
        """
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")

    def _validate_game_player_ids(self, game_id: int, player_id: int):
        """
        Validate that game and player IDs match the replay's IDs.
        
        Args:
            game_id: Game ID to validate
            player_id: Player ID to validate (0 is wildcard)
            
        Raises:
            CorruptReplay: If IDs don't match
        """
        if game_id != self.game_id or (self.player_id != 0 and self.player_id != player_id):
            raise CorruptReplay(f"Game/Player ID mismatch in replay {self.filename}")

    def _validate_timestamp_order(self, time_stamp: datetime):
        """
        Validate that the new timestamp is after the last recorded timestamp.
        
        Args:
            time_stamp: Timestamp to validate
            
        Raises:
            CorruptReplay: If timestamp is out of order
        """
        if self._last_time and self.last_time >= time_stamp:
            raise CorruptReplay(f"Newer patch exists at {self.last_time} than {time_stamp}")

    def _datetime_to_ms(self, dt: datetime) -> int:
        """
        Convert datetime to milliseconds timestamp.
        
        Args:
            dt: Datetime to convert
            
        Returns:
            Timestamp in milliseconds
        """
        return int(dt.timestamp() * MS_PER_SECOND)

    def _jump_from_to(self, start: int, target: int) -> List[ReplayPatch]:
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
                for (from_ts, to_ts), patch in self._patches.items():
                    if from_ts == current and to_ts > from_ts and to_ts <= target:
                        next_patch = (to_ts, patch)
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
                for (from_ts, to_ts), patch in self._patches.items():
                    if from_ts == current and to_ts < from_ts and to_ts >= target:
                        next_patch = (to_ts, patch)
                        break
                if not next_patch:
                    break  # No more patches available, stop here
                current, patch = next_patch
                patches.append(patch)
                
        return patches

    def jump_from_to(self, start: datetime, target: datetime) -> Tuple[List[ReplayPatch], datetime]:
        """
        Jump between two datetimes, snapping to nearest available timestamps.
        
        Args:
            start: Starting datetime
            target: Target datetime
            
        Returns:
            Tuple of (list of patches to apply, actual target datetime reached)
        """
        start_ms = int(start.timestamp() * MS_PER_SECOND)
        target_ms = int(target.timestamp() * MS_PER_SECOND)

        # Snap to nearest available timestamps
        start_ms = max([ts for ts in self._timestamps + [self._start_time] if ts <= start_ms], default=self._start_time)
        target_ms = max([ts for ts in self._timestamps if ts <= target_ms], default=self._start_time)

        return self._jump_from_to(start_ms, target_ms), datetime.fromtimestamp(target_ms / MS_PER_SECOND, tz=UTC)

    def _write_game_state(self, time_stamp: int, game_state: dict):
        """
        Store a complete game state snapshot to disk.
        
        Game states are compressed using zlib to reduce storage size.
        
        Args:
            time_stamp: Timestamp in milliseconds
            game_state: Game state dictionary to store
        """
        self._game_state_timestamps.append(time_stamp)
        self._game_state_timestamps.sort()
        compressed_data = zlib.compress(json.dumps(game_state).encode('utf-8'))
        self.conn.execute(
            f"INSERT INTO {TABLE_GAME_STATE} (timestamp, data) VALUES (?, ?)", 
            (time_stamp, compressed_data))
        self.conn.commit()

    def _write_patch(self, from_timestamp: int, to_timestamp: int, patch: str):
        """
        Store a patch to both memory and disk.
        
        Args:
            from_timestamp: Starting timestamp in milliseconds
            to_timestamp: Ending timestamp in milliseconds
            patch: Serialized patch string
        """
        if (from_timestamp, to_timestamp) in self._patches:
            logger.info(f"Patch for {from_timestamp} to {to_timestamp} already exists, skipping")
            return
        patch_obj = ReplayPatch.from_string(patch)
        self._patches[(from_timestamp, to_timestamp)] = patch_obj
        if to_timestamp not in self._timestamps:
            self._timestamps.append(to_timestamp)
            self._timestamps.sort()
        self.conn.execute(
            f"INSERT INTO {TABLE_PATCHES} (from_timestamp, to_timestamp, patch) VALUES (?, ?, ?)",
            (from_timestamp, to_timestamp, patch)
        )
        self.conn.commit()

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
        if (from_timestamp, to_timestamp) in self._patches:
            return self._patches[(from_timestamp, to_timestamp)]
        raise Exception(f"No patch found with from_timestamp {from_timestamp} and to_timestamp {to_timestamp}")

    def get_timestamps(self) -> List[int]:
        """
        Get all timestamps where patches exist.
        
        Returns:
            Sorted list of timestamps in milliseconds
        """
        return self._timestamps.copy()

    def get_game_state_timestamps(self) -> List[int]:
        """
        Get all timestamps where complete game states are stored.
        
        Returns:
            Sorted list of timestamps in milliseconds
        """
        return self._game_state_timestamps.copy()

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
        self._validate_write_mode()
        self._validate_game_player_ids(game_id, player_id)
        self._validate_timestamp_order(time_stamp)

        time_stamp_ms = self._datetime_to_ms(time_stamp)
        self._write_patch(self._last_time or self._start_time, time_stamp_ms, replay_patch.forward_to_string())
        self._write_patch(time_stamp_ms, self._last_time or self._start_time, replay_patch.backward_to_string())
        self._last_time = time_stamp_ms
        self._write_information()

    def record_initial_game_state(self, time_stamp: datetime, game_id: int, player_id: int, game_state: dict):
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
        self._validate_write_mode()
        self._validate_game_player_ids(game_id, player_id)
        self._validate_timestamp_order(time_stamp)

        time_stamp_ms = self._datetime_to_ms(time_stamp)
        self._write_game_state(time_stamp_ms, game_state)
        self._start_time = time_stamp_ms
        self._last_time = time_stamp_ms
        self._write_information()

    def record_static_map_data(self, static_map_data: dict, game_id: int, player_id: int):
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
        self._validate_write_mode()
        self._validate_game_player_ids(game_id, player_id)
        
        if self._static_map_data is not None:
            return
            
        self._static_map_data = static_map_data
        compressed_data = zlib.compress(json.dumps(static_map_data).encode('utf-8'))
        self.conn.execute(f"INSERT INTO {TABLE_STATIC_MAP_DATA} (data) VALUES (?)", (compressed_data,))
        self.conn.commit()

    def get_initial_game_state(self) -> dict:
        """
        Retrieve the initial game state.
        
        Returns:
            The game state dictionary from the start of the replay
        """
        return self._get_game_state(self._start_time)

    def get_static_map_data(self) -> dict:
        """
        Retrieve static map data.
        
        Returns:
            The static map data dictionary, or empty dict if not set
        """
        return self._static_map_data or {}

    def _get_game_state(self, timestamp: int) -> dict:
        """
        Load a game state from disk.
        
        Args:
            timestamp: Timestamp in milliseconds
            
        Returns:
            Game state dictionary
            
        Raises:
            Exception: If no game state found at the timestamp
        """
        cursor = self.conn.execute(f"SELECT data FROM {TABLE_GAME_STATE} WHERE timestamp = ?", (timestamp,))
        row = cursor.fetchone()
        if row:
            return json.loads(zlib.decompress(row[0]).decode('utf-8'))
        raise Exception(f"No game state found at {timestamp}")