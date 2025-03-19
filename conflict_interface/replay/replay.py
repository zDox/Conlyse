import json
import sqlite3
import os
import zlib
from collections import defaultdict
from datetime import UTC, datetime
from sqlite3 import Connection
from time import time
from typing import Literal

import jsonpatch
from jsonpatch import JsonPatch

from conflict_interface.data_types.custom_types import DateTimeMillisecondsStr
from conflict_interface.data_types.game_object import dump_date_time_str  # Assuming this exists in your codebase
from conflict_interface.replay.replay_patch import ReplayPatch


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
        self.game_state = {}
        self.game_id = game_id
        self.player_id = player_id
        self.conn: Connection | None = None
        self.static_map_data = {}

        self._start_time: int = 0
        self._current_time: int | None = None
        self._last_time: int | None = None  # To track the previous timestamp for patch ranges

    @property
    def start_time(self) -> datetime | None:
        if self._start_time is None:
            return None
        return datetime.fromtimestamp(self._start_time / 1000, tz=UTC)

    @property
    def current_time(self) -> datetime | None:
        if self._current_time is None:
            return None
        return datetime.fromtimestamp(self._current_time / 1000, tz=UTC)

    @property
    def last_time(self) -> datetime | None:
        if self._last_time is None:
            return None
        return datetime.fromtimestamp(self._last_time / 1000, tz=UTC)

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
        elif self.mode == 'a':
            self._load_information()
        elif self.mode == 'r':
            self._load_information()
            self._load_existing_replay()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def open(self):
        self.__enter__()

    def close(self):
        self.__exit__(None, None, None)

    def _create_tables(self):
        """Create SQLite tables for metadata, initial state, patches, actions, and static map data."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS information (
                id INTEGER PRIMARY KEY,  -- Single row with id=1
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
                data BLOB  -- Compressed JSON
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS patches (
                from_timestamp INTEGER,
                to_timestamp INTEGER,
                patch TEXT  -- Uncompressed JSON patch
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                timestamp INTEGER PRIMARY KEY,
                action TEXT  -- Uncompressed JSON action
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS static_map_data (
                data BLOB  -- Compressed JSON
            )
        """)
        self.conn.commit()

    def _write_information(self):
        """Write metadata to the information table."""
        self.conn.execute("""
                INSERT OR REPLACE INTO information (id, version, game_id, player_id, start_time, last_time) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (1, VERSION, self.game_id, self.player_id, self._start_time, self._last_time))
        self.conn.commit()
        print(f"Wrote information to {self._start_time}")

    def _load_information(self):
        """Load metadata from the information table."""
        cursor = self.conn.execute(
            "SELECT version, game_id, player_id, start_time, last_time FROM information WHERE id = ?", (1,))
        row = cursor.fetchone()
        if not row:
            raise CorruptReplay("Information table is empty")

        version, self.game_id, self.player_id, self._start_time, self._last_time = row
        print(row)
        if version != VERSION:
            raise CorruptReplay(f"Unsupported version {version}")

    def _load_existing_replay(self):
        """Load metadata, initial state, static map data, and patch timestamps."""
        self._load_initial_game_state()

        # Load static map data (if present)
        cursor = self.conn.execute("SELECT data FROM static_map_data")
        if static_data := cursor.fetchone():
            self.static_map_data = json.loads(zlib.decompress(static_data[0]).decode('utf-8'))


    def _load_till_uptodate(self):
        self._jump_to(self._last_time)

    def _jump_to(self, target: int):
        """Jump from current_time to target time (in milliseconds) using the shortest path."""
        if self.mode not in ('r', 'a'):
            raise IOError("Replay must be in read or append mode to jump")

        # If no current time, start from initial state
        if self._current_time is None:
            self._load_initial_game_state()

        if target == self._current_time:
            return
        print(target, self._current_time)

        if target < self._start_time:
            raise ValueError(f"Cannot jump to {target} before start time {self._start_time}")

        t1 = time()
        # Sequential Path: Apply patches from current_time to target
        if target > self._current_time:
            cursor = self.conn.execute("""
                        SELECT from_timestamp, to_timestamp, patch 
                        FROM patches 
                        WHERE to_timestamp <= ? AND from_timestamp >= ?
                        AND from_timestamp < to_timestamp 
                        ORDER BY from_timestamp ASC
                    """, (target, self._current_time))
            patches = cursor.fetchall()
            for from_ts, to_ts, patch_str in patches:
                if from_ts != self._current_time:
                    continue
                print(f"Jumping from {from_ts} to {to_ts}")
                patch = JsonPatch.from_string(json.loads(patch_str))
                patch.apply(self.game_state, in_place=True)
                self._current_time = to_ts
                if to_ts == target:
                    continue

            # Sequential Path: Apply patches from current_time to target
        elif target < self._current_time:
            cursor = self.conn.execute("""
                        SELECT from_timestamp, to_timestamp, patch 
                        FROM patches 
                        WHERE to_timestamp <= ? AND from_timestamp >= ?
                        AND from_timestamp > to_timestamp 
                        ORDER BY from_timestamp DESC
                    """, (target, self._current_time))
            patches = cursor.fetchall()
            for from_ts, to_ts, patch_str in patches:
                if from_ts != self._current_time:
                    continue
                print(f"Jumping from {from_ts} to {to_ts}")
                patch = JsonPatch.from_string(json.loads(patch_str))
                patch.apply(self.game_state, in_place=True)
                self._current_time = to_ts


    def jump_to(self, target: datetime) -> dict:
        target = int(target.timestamp() * 1000)
        print(f"Searching for target {target}")
        cursor = self.conn.execute("""
                SELECT to_timestamp 
                FROM patches 
                WHERE to_timestamp <= ?
                ORDER BY to_timestamp DESC
            """, (target,))

        result = cursor.fetchone()
        print(f"Jump res {result}")
        target = result[0] if result else self._start_time
        print(f"Jumping to {target}")
        self._jump_to(target)
        return self.game_state

    def _load_initial_game_state(self):
        """Load and decompress the initial game state."""
        print(f"Intitial GameState: {self._start_time}")
        cursor = self.conn.execute("SELECT timestamp, data FROM game_state where timestamp=?", (self._start_time, ))
        initial_data = cursor.fetchone()
        if initial_data is None:
            raise CorruptReplay("No initial state found")
        self.game_state = json.loads(zlib.decompress(initial_data[1]).decode('utf-8'))
        self._current_time = initial_data[0]

    def _write_game_state(self, time_stamp: int, game_state: dict):
        compressed_data = zlib.compress(json.dumps(game_state).encode('utf-8'))
        self.conn.execute("INSERT INTO game_state (timestamp, data) VALUES (?, ?)", (time_stamp, compressed_data,))
        self.conn.commit()

    def _write_initial_game_state(self, time_stamp: int, game_state: dict):
        """Compress and write the initial game state."""
        compressed_data = zlib.compress(json.dumps(game_state).encode('utf-8'))
        self.conn.execute("INSERT INTO game_state (timestamp, data) VALUES (?, ?)", (time_stamp, compressed_data,))
        self.conn.commit()
        self._start_time = time_stamp
        self._current_time = time_stamp
        self._last_time = time_stamp

    def _write_patch(self, from_timestamp: int, to_timestamp: int, patch: str):
        """Write a patch to the database with from and to timestamps."""
        cursor = self.conn.execute("SELECT 1 FROM patches WHERE from_timestamp = ? and to_timestamp = ?",
                                   (from_timestamp, to_timestamp,))
        if cursor.fetchone():
            print(f"Patch for to_timestamp {to_timestamp} already exists, skipping")
            return
        self.conn.execute(
            "INSERT INTO patches (from_timestamp, to_timestamp, patch) VALUES (?, ?, ?)",
            (from_timestamp, to_timestamp, patch)
        )
        self.conn.commit()

    def _get_patch(self, from_timestamp: int, to_timestamp: int) -> ReplayPatch:
        cursor = self.conn.execute("""
                SELECT  
                patch
                FROM patches 
                WHERE from_timestamp = ? and to_timestamp = ?
            """, (from_timestamp, to_timestamp,))
        result = cursor.fetchone()
        if result:
            return ReplayPatch.from_string(result[0])
        else:
            raise Exception(f"No patch found with from_timestamp {from_timestamp} and to_timestamp {to_timestamp}")

    def _get_game_state(self, timestamp: int) -> dict:
        cursor = self.conn.execute("""
                SELECT  
                data
                FROM game_state 
                WHERE timestamp = ?
            """, (timestamp,))
        result = cursor.fetchone()
        if result:
            return json.loads(zlib.decompress(result[0]).decode('utf-8'))
        else:
            raise Exception(f"No Game found with timestamp {timestamp}")

    def get_static_map_data(self) -> dict:
        """Return the static map data."""
        return self.static_map_data

    def record_patch(self, time_stamp: datetime, game_id: int, player_id: int, replay_patch: ReplayPatch):
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Game ID or Player ID do not match replay {self.filename}")
        if self._last_time and self.last_time >= time_stamp:
            raise CorruptReplay(f"Already recorded newer ReplayPatch at {self.last_time} then {time_stamp}.")

        time_stamp_ms = int(time_stamp.timestamp() * 1000)
        self._write_patch(self._last_time, time_stamp_ms, replay_patch.to_string())
        self._last_time = time_stamp_ms
        self._write_information()
        print(f"Recorded patch at {time_stamp}")

    def record_initial_game_state(self, time_stamp: datetime, game_id: int, player_id: int, game_state: dict):
        """Record a game state, either as initial state or a patch with from/to timestamps."""
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Game ID or Player ID do not match replay {self.filename}")
        if self._last_time and self.last_time >= time_stamp:
            raise CorruptReplay(f"Already recorded newer GameState at {self.last_time} then {time_stamp}.")

        time_stamp_ms = int(time_stamp.timestamp() * 1000)
        self._write_initial_game_state(time_stamp_ms, game_state)
        self._last_time = time_stamp_ms
        self._write_information()
        print(f"Recording intial game state at {self._start_time}.")

    def record_game_state(self, time_stamp: datetime, game_id: int, player_id: int, game_state: dict):
        """Record a game state, either as initial state or a patch with from/to timestamps."""
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Game ID or Player ID do not match replay {self.filename}")
        if self.last_time and self.last_time >= time_stamp:
            raise CorruptReplay(f"Already recorded newer GameState at {self.last_time} then {time_stamp}.")

        time_stamp_ms = int(time_stamp.timestamp() * 1000)
        self._write_game_state(time_stamp_ms, game_state)
        self._last_time = time_stamp_ms
        self._write_information()

    def record_static_map_data(self, static_map_data: dict, game_id: int, player_id: int):
        """Compress and record static map data."""
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Game ID or Player ID do not match replay {self.filename}")

        cursor = self.conn.execute("SELECT 1 FROM static_map_data")
        if cursor.fetchone():
            return  # Already recorded

        compressed_data = zlib.compress(json.dumps(static_map_data).encode('utf-8'))
        self.conn.execute("INSERT INTO static_map_data (data) VALUES (?)", (compressed_data,))
        self.conn.commit()