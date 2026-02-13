"""
Database interface for tracking replay metadata.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum


class ReplayStatus(Enum):
    """Status of a replay."""
    RECORDING = "recording"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ReplayDatabase:
    """Manages replay metadata in SQLite database."""
    
    def __init__(self, db_path: Path):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self):
        """Connect to the database and create tables if needed."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                replay_name TEXT NOT NULL UNIQUE,
                hot_storage_path TEXT,
                cold_storage_path TEXT,
                status TEXT NOT NULL,
                recording_start_time TEXT,
                recording_end_time TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                response_count INTEGER DEFAULT 0,
                UNIQUE(game_id, player_id)
            )
        """)
        
        self.conn.commit()
        
    def create_replay_entry(self, game_id: int, player_id: int, 
                           replay_name: str, hot_storage_path: str,
                           recording_start_time: Optional[datetime] = None) -> int:
        """
        Create a new replay entry in the database.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            replay_name: Unique name for the replay
            hot_storage_path: Path to the replay file in hot storage
            recording_start_time: When recording started
            
        Returns:
            The ID of the created entry
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO replays 
            (game_id, player_id, replay_name, hot_storage_path, status, 
             recording_start_time, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id, player_id, replay_name, hot_storage_path,
            ReplayStatus.RECORDING.value,
            recording_start_time.isoformat() if recording_start_time else now,
            now, now
        ))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def get_replay_by_game_and_player(self, game_id: int, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get replay entry by game_id and player_id.
        
        Args:
            game_id: Game ID
            player_id: Player ID
            
        Returns:
            Dictionary with replay data or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM replays 
            WHERE game_id = ? AND player_id = ?
        """, (game_id, player_id))
        
        row = cursor.fetchone()
        return dict(row) if row else None
        
    def update_replay_status(self, replay_id: int, status: ReplayStatus,
                            recording_end_time: Optional[datetime] = None,
                            cold_storage_path: Optional[str] = None):
        """
        Update the status of a replay.
        
        Args:
            replay_id: Database ID of the replay
            status: New status
            recording_end_time: When recording ended (optional)
            cold_storage_path: Path in cold storage (optional)
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        if recording_end_time and cold_storage_path:
            cursor.execute("""
                UPDATE replays 
                SET status = ?, recording_end_time = ?, cold_storage_path = ?, updated_at = ?
                WHERE id = ?
            """, (status.value, recording_end_time.isoformat(), cold_storage_path, now, replay_id))
        elif recording_end_time:
            cursor.execute("""
                UPDATE replays 
                SET status = ?, recording_end_time = ?, updated_at = ?
                WHERE id = ?
            """, (status.value, recording_end_time.isoformat(), now, replay_id))
        elif cold_storage_path:
            cursor.execute("""
                UPDATE replays 
                SET status = ?, cold_storage_path = ?, updated_at = ?
                WHERE id = ?
            """, (status.value, cold_storage_path, now, replay_id))
        else:
            cursor.execute("""
                UPDATE replays 
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status.value, now, replay_id))
        
        self.conn.commit()
        
    def increment_response_count(self, replay_id: int, count: int = 1):
        """
        Increment the response count for a replay.
        
        Args:
            replay_id: Database ID of the replay
            count: Number to increment by (default: 1)
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE replays 
            SET response_count = response_count + ?, updated_at = ?
            WHERE id = ?
        """, (count, now, replay_id))
        
        self.conn.commit()
        
    def get_all_active_replays(self) -> List[Dict[str, Any]]:
        """
        Get all replays that are currently recording.
        
        Returns:
            List of replay dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM replays 
            WHERE status = ?
        """, (ReplayStatus.RECORDING.value,))
        
        return [dict(row) for row in cursor.fetchall()]
