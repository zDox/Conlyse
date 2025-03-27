import json
import sqlite3
import os
import zlib
from datetime import UTC, datetime
from sqlite3 import Connection
from typing import Literal, Dict, List, Optional

from conflict_interface.logger_config import get_logger
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch, ReplayPatch

logger = get_logger()


class CorruptReplay(Exception):
    pass


VERSION = 3
MANDATORY_KEYS = ["version", "game_id", "player_id", "start_time"]


class Replay:
    def __init__(self, filename: str, mode: Literal['r', 'w', 'a'], game_id: int = None, player_id: int = None):
        if mode not in ('r', 'w', 'a'):
            raise ValueError("Mode must be 'r' (read), 'w' (write), or 'a' (append)")

        self.filename = filename
        self.mode = mode
        self.game_id = game_id
        self.player_id = player_id
        self.conn: Optional[Connection] = None

        self._start_time: int = 0
        self._last_time: Optional[int] = None

        # In-memory caches
        self._patches: Dict[tuple[int, int], ReplayPatch] = {}  # (from_ts, to_ts) -> patch
        self._game_states: Dict[int, dict] = {}  # timestamp -> game state
        self._static_map_data: Optional[dict] = None
        self._timestamps: List[int] = []
        self._game_state_timestamps: List[int] = []

    def __enter__(self):
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
            self._load_into_memory()  # Load data into memory
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def open(self):
        self.__enter__()

    def close(self):
        self.__exit__(None, None, None)

    def _load_into_memory(self):
        """Load critical tables into memory for faster access."""
        # Load game states
        cursor = self.conn.execute("SELECT timestamp, data FROM game_state")
        for timestamp, compressed_data in cursor.fetchall():
            self._game_states[timestamp] = json.loads(zlib.decompress(compressed_data).decode('utf-8'))
            self._game_state_timestamps.append(timestamp)
        self._game_state_timestamps.sort()

        # Load patches
        cursor = self.conn.execute("SELECT from_timestamp, to_timestamp, patch FROM patches")
        for from_ts, to_ts, patch_str in cursor.fetchall():
            self._patches[(from_ts, to_ts)] = ReplayPatch.from_string(patch_str)
            if to_ts not in self._timestamps:
                self._timestamps.append(to_ts)
        self._timestamps.sort()

        # Load static map data
        cursor = self.conn.execute("SELECT data FROM static_map_data")
        if static_data := cursor.fetchone():
            self._static_map_data = json.loads(zlib.decompress(static_data[0]).decode('utf-8'))

    def _create_tables(self):
        """Create SQLite tables (unchanged)."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS information (
                id INTEGER PRIMARY KEY,
                version INTEGER,
                game_id INTEGER,
                player_id INTEGER,
                start_time INTEGER,
                last_time INTEGER
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS game_state (
                timestamp INTEGER PRIMARY KEY,
                data BLOB
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS patches (
                from_timestamp INTEGER,
                to_timestamp INTEGER,
                patch TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                timestamp INTEGER PRIMARY KEY,
                action TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS static_map_data (
                data BLOB
            )
        """)
        self.conn.commit()

    @property
    def start_time(self) -> Optional[datetime]:
        return datetime.fromtimestamp(self._start_time / 1000, tz=UTC) if self._start_time else None

    @property
    def last_time(self) -> Optional[datetime]:
        return datetime.fromtimestamp(self._last_time / 1000, tz=UTC) if self._last_time else None

    def _write_information(self):
        """Write metadata to the information table."""
        self.conn.execute("""
            INSERT OR REPLACE INTO information (id, version, game_id, player_id, start_time, last_time) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (1, VERSION, self.game_id, self.player_id, self._start_time, self._last_time))
        self.conn.commit()

    def _load_information(self):
        """Load metadata from the information table."""
        cursor = self.conn.execute(
            "SELECT version, game_id, player_id, start_time, last_time FROM information WHERE id = ?", (1,))
        row = cursor.fetchone()
        if not row:
            raise CorruptReplay("Information table is empty")
        version, self.game_id, self.player_id, self._start_time, self._last_time = row
        if version != VERSION:
            raise CorruptReplay(f"Unsupported version {version}")

    def _jump_from_to(self, start: int, target: int) -> List[ReplayPatch]:
        """Jump from start to target using in-memory patches."""
        if self.mode not in ('r', 'a'):
            raise IOError("Replay must be in read or append mode to jump")
        if target < self._start_time:
            raise ValueError(f"Cannot jump to {target} before start time {self._start_time}")

        patches = []
        current = start
        if target > start:
            while current < target:
                next_patch = None
                for (from_ts, to_ts), patch in self._patches.items():
                    if from_ts == current and to_ts > from_ts and to_ts <= target:
                        next_patch = (to_ts, patch)
                        break
                if not next_patch:
                    break
                current, patch = next_patch
                patches.append(patch)
        elif target < start:
            while current > target:
                next_patch = None
                for (from_ts, to_ts), patch in self._patches.items():
                    if from_ts == current and to_ts < from_ts and to_ts >= target:
                        next_patch = (to_ts, patch)
                        break
                if not next_patch:
                    break
                current, patch = next_patch
                patches.append(patch)
        return patches

    def jump_from_to(self, start: datetime, target: datetime) -> List[ReplayPatch]:
        start_ms = int(start.timestamp() * 1000)
        target_ms = int(target.timestamp() * 1000)

        # Snap to nearest available timestamps
        start_ms = max([ts for ts in self._timestamps + [self._start_time] if ts <= start_ms], default=self._start_time)
        target_ms = max([ts for ts in self._timestamps if ts <= target_ms], default=self._start_time)

        return self._jump_from_to(start_ms, target_ms)

    def _write_game_state(self, time_stamp: int, game_state: dict):
        """Write to both memory and disk."""
        self._game_states[time_stamp] = game_state
        self._game_state_timestamps.append(time_stamp)
        self._game_state_timestamps.sort()
        compressed_data = zlib.compress(json.dumps(game_state).encode('utf-8'))
        self.conn.execute("INSERT INTO game_state (timestamp, data) VALUES (?, ?)", (time_stamp, compressed_data))
        self.conn.commit()

    def _write_patch(self, from_timestamp: int, to_timestamp: int, patch: str):
        """Write to both memory and disk."""
        if (from_timestamp, to_timestamp) in self._patches:
            logger.info(f"Patch for {from_timestamp} to {to_timestamp} already exists, skipping")
            return
        patch_obj = ReplayPatch.from_string(patch)
        self._patches[(from_timestamp, to_timestamp)] = patch_obj
        if to_timestamp not in self._timestamps:
            self._timestamps.append(to_timestamp)
            self._timestamps.sort()
        self.conn.execute(
            "INSERT INTO patches (from_timestamp, to_timestamp, patch) VALUES (?, ?, ?)",
            (from_timestamp, to_timestamp, patch)
        )
        self.conn.commit()

    def get_patch(self, from_timestamp: int, to_timestamp: int) -> ReplayPatch:
        if (from_timestamp, to_timestamp) in self._patches:
            return self._patches[(from_timestamp, to_timestamp)]
        raise Exception(f"No patch found with from_timestamp {from_timestamp} and to_timestamp {to_timestamp}")

    def get_timestamps(self) -> List[int]:
        return self._timestamps.copy()

    def get_game_state_timestamps(self) -> List[int]:
        return self._game_state_timestamps.copy()

    def record_bipatch(self, time_stamp: datetime, game_id: int, player_id: int,
                       replay_patch: BidirectionalReplayPatch):
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or (self.player_id != 0 and self.player_id != player_id):
            raise CorruptReplay(f"Game/Player ID mismatch in replay {self.filename}")
        if self._last_time and self.last_time >= time_stamp:
            raise CorruptReplay(f"Newer patch exists at {self.last_time} than {time_stamp}")

        time_stamp_ms = int(time_stamp.timestamp() * 1000)
        self._write_patch(self._last_time or self._start_time, time_stamp_ms, replay_patch.forward_to_string())
        self._write_patch(time_stamp_ms, self._last_time or self._start_time, replay_patch.backward_to_string())
        self._last_time = time_stamp_ms
        self._write_information()

    def record_initial_game_state(self, time_stamp: datetime, game_id: int, player_id: int, game_state: dict):
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or (self.player_id != 0 and self.player_id != player_id):
            raise CorruptReplay(f"Game/Player ID mismatch in replay {self.filename}")
        if self._last_time and self.last_time >= time_stamp:
            raise CorruptReplay(f"Newer state exists at {self.last_time} than {time_stamp}")

        time_stamp_ms = int(time_stamp.timestamp() * 1000)
        self._write_game_state(time_stamp_ms, game_state)
        self._start_time = time_stamp_ms
        self._last_time = time_stamp_ms
        self._write_information()

    def record_static_map_data(self, static_map_data: dict, game_id: int, player_id: int):
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or (self.player_id != 0 and self.player_id != player_id):
            raise CorruptReplay(f"Game/Player ID mismatch in replay {self.filename}")
        if self._static_map_data is not None:
            return
        self._static_map_data = static_map_data
        compressed_data = zlib.compress(json.dumps(static_map_data).encode('utf-8'))
        self.conn.execute("INSERT INTO static_map_data (data) VALUES (?)", (compressed_data,))
        self.conn.commit()

    def get_initial_game_state(self) -> dict:
        if self._start_time in self._game_states:
            return self._game_states[self._start_time]
        raise Exception(f"No game state found at {self._start_time}")

    def get_static_map_data(self) -> dict:
        return self._static_map_data or {}

    def _get_game_state(self, timestamp: int) -> dict:
        if timestamp in self._game_states:
            return self._game_states[timestamp]
        raise Exception(f"No game state found at {timestamp}")