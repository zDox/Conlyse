"""
Database interface for tracking replay metadata.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReplayStatus(Enum):
    """Status of a replay."""
    RECORDING = "recording"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ReplayDatabase:
    """Manages replay metadata in PostgreSQL or SQLite database."""
    
    def __init__(self, db_config: Union[Path, Dict[str, Any]]):
        """
        Initialize the database connection.
        
        Args:
            db_config: Either a Path to SQLite database file, or a dict with PostgreSQL config:
                      {'host': 'localhost', 'port': 5432, 'database': 'replays',
                       'user': 'user', 'password': 'pass'}
        """
        if isinstance(db_config, (Path, str)):
            # SQLite mode
            self.db_type = 'sqlite'
            self.db_path = Path(db_config)
            self.db_config = None
        else:
            # PostgreSQL mode
            self.db_type = 'postgres'
            self.db_path = None
            self.db_config = db_config
            
        self.conn = None
        
    def connect(self):
        """Connect to the database and create tables if needed."""
        if self.db_type == 'sqlite':
            import sqlite3
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        else:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
            except ImportError:
                raise ImportError(
                    "psycopg2 is required for PostgreSQL support. "
                    "Install it with: pip install psycopg2-binary"
                )
            
            self.conn = psycopg2.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5432),
                database=self.db_config.get('database', 'replays'),
                user=self.db_config.get('user', 'postgres'),
                password=self.db_config.get('password', '')
            )
            self.conn.cursor_factory = RealDictCursor
            
        self._create_tables()
        
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _get_placeholder(self) -> str:
        """Get the appropriate SQL placeholder for the database type."""
        return '?' if self.db_type == 'sqlite' else '%s'
    
    def _format_query(self, query_template: str, num_params: int) -> str:
        """
        Format a SQL query with the appropriate placeholders.
        
        Args:
            query_template: Query with {} placeholders
            num_params: Number of parameters in the query
            
        Returns:
            Formatted query with proper placeholders
        """
        placeholder = self._get_placeholder()
        return query_template.format(*[placeholder] * num_params)
            
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        if self.db_type == 'sqlite':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS replays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    player_id INTEGER NOT NULL,
                    replay_name TEXT NOT NULL UNIQUE,
                    hot_storage_path TEXT,
                    cold_storage_path TEXT,
                    status TEXT NOT NULL,
                    recording_start_time TIMESTAMP,
                    recording_end_time TIMESTAMP,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    response_count INTEGER DEFAULT 0,
                    UNIQUE(game_id, player_id)
                )
            """)
        else:
            # PostgreSQL schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS replays (
                    id SERIAL PRIMARY KEY,
                    game_id INTEGER NOT NULL,
                    player_id INTEGER NOT NULL,
                    replay_name VARCHAR(255) NOT NULL UNIQUE,
                    hot_storage_path TEXT,
                    cold_storage_path TEXT,
                    status VARCHAR(50) NOT NULL,
                    recording_start_time TIMESTAMP,
                    recording_end_time TIMESTAMP,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
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
        now = datetime.now()
        
        if self.db_type == 'sqlite':
            cursor.execute("""
                INSERT INTO replays 
                (game_id, player_id, replay_name, hot_storage_path, status, 
                 recording_start_time, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_id, player_id, replay_name, hot_storage_path,
                ReplayStatus.RECORDING.value,
                recording_start_time if recording_start_time else now,
                now, now
            ))
            replay_id = cursor.lastrowid
        else:
            # PostgreSQL uses %s placeholders and RETURNING for getting the ID
            cursor.execute("""
                INSERT INTO replays 
                (game_id, player_id, replay_name, hot_storage_path, status, 
                 recording_start_time, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                game_id, player_id, replay_name, hot_storage_path,
                ReplayStatus.RECORDING.value,
                recording_start_time if recording_start_time else now,
                now, now
            ))
            replay_id = cursor.fetchone()['id']
        
        self.conn.commit()
        return replay_id
        
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
        
        query = self._format_query("""
            SELECT * FROM replays 
            WHERE game_id = {} AND player_id = {}
        """, 2)
        cursor.execute(query, (game_id, player_id))
        
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
        now = datetime.now()
        
        if recording_end_time and cold_storage_path:
            query = self._format_query("""
                UPDATE replays 
                SET status = {}, recording_end_time = {}, 
                    cold_storage_path = {}, updated_at = {}
                WHERE id = {}
            """, 5)
            cursor.execute(query, (status.value, recording_end_time, cold_storage_path, now, replay_id))
        elif recording_end_time:
            query = self._format_query("""
                UPDATE replays 
                SET status = {}, recording_end_time = {}, updated_at = {}
                WHERE id = {}
            """, 4)
            cursor.execute(query, (status.value, recording_end_time, now, replay_id))
        elif cold_storage_path:
            query = self._format_query("""
                UPDATE replays 
                SET status = {}, cold_storage_path = {}, updated_at = {}
                WHERE id = {}
            """, 4)
            cursor.execute(query, (status.value, cold_storage_path, now, replay_id))
        else:
            query = self._format_query("""
                UPDATE replays 
                SET status = {}, updated_at = {}
                WHERE id = {}
            """, 3)
            cursor.execute(query, (status.value, now, replay_id))
        
        self.conn.commit()
        
    def increment_response_count(self, replay_id: int, count: int = 1):
        """
        Increment the response count for a replay.
        
        Args:
            replay_id: Database ID of the replay
            count: Number to increment by (default: 1)
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        
        query = self._format_query("""
            UPDATE replays 
            SET response_count = response_count + {}, updated_at = {}
            WHERE id = {}
        """, 3)
        cursor.execute(query, (count, now, replay_id))
        
        self.conn.commit()
        
    def get_all_active_replays(self) -> List[Dict[str, Any]]:
        """
        Get all replays that are currently recording.
        
        Returns:
            List of replay dictionaries
        """
        cursor = self.conn.cursor()
        
        query = self._format_query("""
            SELECT * FROM replays 
            WHERE status = {}
        """, 1)
        cursor.execute(query, (ReplayStatus.RECORDING.value,))
        
        return [dict(row) for row in cursor.fetchall()]
