import json
import sqlite3
import os
import zlib
from collections import defaultdict
from datetime import UTC, datetime
from time import time
from typing import Literal

import jsonpatch
from jsonpatch import JsonPatch

from conflict_interface.data_types.custom_types import DateTimeMillisecondsStr
from conflict_interface.data_types.game_object import dump_date_time_str  # Assuming this exists in your codebase


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
        self.game_state = defaultdict(dict)  # Defaultdict for consistency with your original
        self.time_stamps = []
        self.game_id = game_id
        self.player_id = player_id
        self.conn = None  # SQLite connection
        self.start_time = None
        self.static_map_data = defaultdict(dict)  # Defaultdict for consistency

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
            self._load_existing_replay()
            self._load_till_uptodate()
        elif self.mode == 'r':
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
                version INTEGER,
                game_id INTEGER,
                player_id INTEGER,
                start_time TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS initial_state (
                data BLOB  -- Compressed JSON
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS patches (
                timestamp INTEGER PRIMARY KEY,
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
        self.start_time = datetime.now(tz=UTC)
        self.conn.execute(
            "INSERT INTO information (version, game_id, player_id, start_time) VALUES (?, ?, ?, ?)",
            (VERSION, self.game_id, self.player_id, dump_date_time_str(self.start_time))
        )
        self.conn.commit()

    def _load_information(self):
        """Load metadata from the information table."""
        cursor = self.conn.execute("SELECT version, game_id, player_id, start_time FROM information")
        row = cursor.fetchone()
        if not row:
            raise CorruptReplay("Information table is empty")

        version, game_id, player_id, start_time = row
        if version != VERSION:
            raise CorruptReplay(f"Unsupported version {version}")
        if not all(k in locals() for k in MANDATORY_KEYS):
            raise CorruptReplay("Missing keys in information table")

        self.game_id = game_id
        self.player_id = player_id
        self.start_time = datetime.fromisoformat(start_time) if start_time else None

    def _load_existing_replay(self):
        """Load metadata, initial state, static map data, and patch timestamps."""
        self._load_information()

        # Check for initial state
        cursor = self.conn.execute("SELECT data FROM initial_state")
        initial_data = cursor.fetchall()
        if len(initial_data) > 1:
            raise CorruptReplay("Multiple initial states detected")
        if len(initial_data) == 0:
            raise CorruptReplay("No initial state found")
        self._load_initial_game_state()

        # Load static map data (if present)
        cursor = self.conn.execute("SELECT data FROM static_map_data")
        if static_data := cursor.fetchone():
            self.static_map_data = json.loads(zlib.decompress(static_data[0]).decode('utf-8'))

        # Load patch timestamps
        cursor = self.conn.execute("SELECT timestamp FROM patches ORDER BY timestamp")
        self.time_stamps = [row[0] for row in cursor.fetchall()]

    def _load_till_uptodate(self):
        """Apply all patches to bring game_state up to date."""
        for time_stamp in self.time_stamps:
            patch = self._get_patch(time_stamp)
            patch.apply(self.game_state, in_place=True)

    def _load_initial_game_state(self):
        """Load and decompress the initial game state."""
        t1 = time()
        cursor = self.conn.execute("SELECT data FROM initial_state")
        compressed_data = cursor.fetchone()[0]
        self.game_state = json.loads(zlib.decompress(compressed_data).decode('utf-8'))
        print(f"Loaded initial state in {time() - t1:.4f} seconds")

    def _write_initial_game_state(self, time_stamp: int, game_state: dict):
        """Compress and write the initial game state."""
        compressed_data = zlib.compress(json.dumps(game_state).encode('utf-8'))
        self.conn.execute("INSERT INTO initial_state (data) VALUES (?)", (compressed_data,))
        self.conn.commit()
        self.start_time = datetime.fromtimestamp(time_stamp / 1000, tz=UTC)

    def _get_patch(self, time_stamp: int) -> JsonPatch:
        """Retrieve a patch from the database."""
        cursor = self.conn.execute("SELECT patch FROM patches WHERE timestamp = ?", (time_stamp,))
        patch_str = cursor.fetchone()
        if not patch_str:
            raise CorruptReplay(f"No patch found for timestamp {time_stamp}")
        return JsonPatch.from_string(json.loads(patch_str[0]))

    def _write_patch(self, time_stamp: int, patch: JsonPatch):
        """Write a patch to the database if it doesn’t exist."""
        cursor = self.conn.execute("SELECT 1 FROM patches WHERE timestamp = ?", (time_stamp,))
        if cursor.fetchone():
            print(f"Patch for timestamp {time_stamp} already exists, skipping")
            return
        self.conn.execute(
            "INSERT INTO patches (timestamp, patch) VALUES (?, ?)",
            (time_stamp, json.dumps(patch.to_string()))
        )
        self.conn.commit()

    def load_game_state(self, time_stamp: datetime) -> dict:
        """Load the game state up to a specific timestamp."""
        target_time_stamp = int(time_stamp.timestamp() * 1000)
        relevant_patch = next(
            (t for t in self.time_stamps if t > target_time_stamp),
            self.time_stamps[-1] if self.time_stamps else None
        )

        self._load_initial_game_state()  # Reset to initial state
        if relevant_patch is None:
            return self.game_state

        cursor = self.conn.execute(
            "SELECT patch FROM patches WHERE timestamp <= ? ORDER BY timestamp",
            (target_time_stamp,)
        )
        for patch_str in cursor.fetchall():
            patch = JsonPatch.from_string(json.loads(patch_str[0]))
            patch.apply(self.game_state, in_place=True)
        return self.game_state

    def get_static_map_data(self) -> dict:
        """Return the static map data."""
        return self.static_map_data

    def record_game_state(self, time_stamp: datetime, game_id: int, player_id: int, game_state: dict):
        """Record a game state, either as initial state or a patch."""
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Game ID or Player ID do not match replay {self.filename}")

        time_stamp_ms = int(time_stamp.timestamp() * 1000)
        if not self.game_state:
            self._write_initial_game_state(time_stamp_ms, game_state)
            self.game_state = game_state
        else:
            patch = jsonpatch.make_patch(self.game_state, game_state)
            self._write_patch(time_stamp_ms, patch)
            patch.apply(self.game_state, in_place=True)

    def record_static_map_data(self, static_map_data: dict, game_id: int, player_id: int):
        """Compress and record static map data."""
        if self.mode not in ("w", "a"):
            raise IOError("Replay is not in write or append mode")
        if game_id != self.game_id or player_id != self.player_id:
            raise CorruptReplay(f"Game ID or Player ID do not match replay {self.filename}")

        print("Recording Static Map Data")
        cursor = self.conn.execute("SELECT 1 FROM static_map_data")
        if cursor.fetchone():
            return  # Already recorded

        compressed_data = zlib.compress(json.dumps(static_map_data).encode('utf-8'))
        self.conn.execute("INSERT INTO static_map_data (data) VALUES (?)", (compressed_data,))
        self.conn.commit()
