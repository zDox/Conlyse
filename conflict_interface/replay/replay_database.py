import json
import sqlite3
import zlib
from sqlite3 import Connection
from typing import Optional

from conflict_interface.logger_config import get_logger
from conflict_interface.replay.constants import CorruptReplay
from conflict_interface.replay.replay_metadata import ReplayMetadata
from conflict_interface.replay.replay_patch import ReplayPatch
from conflict_interface.replay.replay_validator import ReplayValidator

logger = get_logger()

# Database table names
TABLE_INFORMATION = "information"
TABLE_GAME_STATE = "game_state"
TABLE_PATCHES = "patches"
TABLE_ACTIONS = "actions"
TABLE_STATIC_MAP_DATA = "static_map_data"

# Information table primary key
INFO_TABLE_PK = 1

class ReplayDatabase:
    """Handles all SQLite database operations for replays."""

    def __init__(self):
        self.conn: Optional[Connection] = None

    def connect(self, filename):
        self.conn = sqlite3.connect(filename)

    def disconnect(self):
        self.conn.close()

    def create_tables(self):
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

    def read_metadata(self) -> ReplayMetadata:
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
        meta = self.row_to_metadata(row)
        ReplayValidator.validate_version(meta.version)
        return meta

    def write_metadata(self, meta: ReplayMetadata):
        """Write or update replay metadata in the information table."""
        self.conn.execute(f"""
            INSERT OR REPLACE INTO {TABLE_INFORMATION} (id, version, game_id, player_id, start_time, last_time) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (INFO_TABLE_PK, meta.version, meta.game_id, meta.player_id, meta.start_time, meta.last_time))
        self.conn.commit()

    def read_patch(self, from_ts: int, to_ts: int) -> ReplayPatch | None:
        """Read patch from database."""
        # Load patch from disk
        cursor = self.conn.execute(
            f"SELECT patch FROM {TABLE_PATCHES} WHERE from_timestamp = ? AND to_timestamp = ?",
            (from_ts, to_ts))
        row = cursor.fetchone()
        if row:
            return ReplayPatch.from_string(row[0])

    def read_patches(self) -> dict[tuple[int, int], ReplayPatch]:
        """Read all patches from database."""
        patches = {}
        cursor = self.conn.execute(f"SELECT from_timestamp, to_timestamp, patch FROM {TABLE_PATCHES}")
        for row in cursor.fetchall():
            from_ts, to_ts, patch_str = row
            patches[(from_ts, to_ts)] = ReplayPatch.from_string(patch_str)
        return patches

    def read_patch_timestamps(self) -> list[tuple[int, int]]:
        """Read all patch timestamps from database."""
        cursor = self.conn.execute(
            f"SELECT from_timestamp, to_timestamp FROM {TABLE_PATCHES} ORDER BY from_timestamp ")
        return cursor.fetchall()

    def write_patch(self, from_ts: int, to_ts: int, patch_str: str):
        """Write patch to database."""

        self.conn.execute(
            f"INSERT INTO {TABLE_PATCHES} (from_timestamp, to_timestamp, patch) VALUES (?, ?, ?)",
            (from_ts, to_ts, patch_str)
        )
        self.conn.commit()

    def read_game_state_timestamps(self):
        cursor = self.conn.execute(f"SELECT timestamp FROM {TABLE_GAME_STATE}")
        return [row[0] for row in cursor.fetchall()]

    def read_game_state(self, timestamp: int) -> dict:
        cursor = self.conn.execute(f"SELECT data FROM {TABLE_GAME_STATE} WHERE timestamp = ?", (timestamp,))
        row = cursor.fetchone()
        if row:
            return json.loads(zlib.decompress(row[0]).decode('utf-8'))
        raise Exception(f"No game state found at {timestamp}")

    def write_game_state(self, timestamp: int, game_state: dict):
        """Write compressed game state."""
        compressed_data = zlib.compress(json.dumps(game_state).encode('utf-8'))
        self.conn.execute(
            f"INSERT INTO {TABLE_GAME_STATE} (timestamp, data) VALUES (?, ?)",
            (timestamp, compressed_data))
        self.conn.commit()

    def read_static_map_data(self) -> dict:
        """
        Load static map data from disk.

        Returns:
            The static map data dictionary, or empty dict if not set
        """
        cursor = self.conn.execute(f"SELECT data FROM {TABLE_STATIC_MAP_DATA}")
        if static_data := cursor.fetchone():
            return json.loads(zlib.decompress(static_data[0]).decode('utf-8'))
        return {}

    def write_static_map_data(self, static_map_data: dict):
        """
        Store static map data to disk.

        Static map data is compressed using zlib to reduce storage size.

        Args:
            static_map_data: Static map data dictionary to store
        """
        # Check if static map data already exists
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {TABLE_STATIC_MAP_DATA}")
        if cursor.fetchone()[0] > 0:
            return

        compressed_data = zlib.compress(json.dumps(static_map_data).encode('utf-8'))
        self.conn.execute(f"INSERT INTO {TABLE_STATIC_MAP_DATA} (data) VALUES (?)", (compressed_data,))
        self.conn.commit()

    @staticmethod
    def row_to_metadata(row) -> ReplayMetadata:
        """Convert a database row to ReplayMetadata."""
        return ReplayMetadata(
            version=row[0],
            game_id=row[1],
            player_id=row[2],
            start_time=row[3],
            last_time=row[4]
        )