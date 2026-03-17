"""
Database interface for tracking replay metadata in PostgreSQL.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Iterable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReplayStatus(Enum):
    """Status of a replay."""
    RECORDING = "recording"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ReplayDatabase:
    """Manages replay metadata in PostgreSQL database."""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize the database connection.
        
        Args:
            db_config: PostgreSQL configuration dict:
                      {'host': 'localhost', 'port': 5432, 'database': 'replays',
                       'user': 'user', 'password': 'pass'}
        """
        self.db_config = db_config
        self.conn = None
        
    def connect(self):
        """Connect to the database and create tables if needed."""
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
            password=self.db_config.get('password', ''),
            cursor_factory=RealDictCursor
        )
        
        self._create_tables()
        
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _format_query(self, query_template: str, num_params: int) -> str:
        """
        Format a SQL query with PostgreSQL placeholders (%s).
        
        Args:
            query_template: Query with {} placeholders
            num_params: Number of parameters in the query
            
        Returns:
            Formatted query with %s placeholders
        """
        return query_template.format(*['%s'] * num_params)
            
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # PostgreSQL schema
        # Replays table: status_observer (observer), status_converter (converter), failed timestamps.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS replays (
                id SERIAL PRIMARY KEY,
                game_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                replay_name VARCHAR(255) NOT NULL UNIQUE,
                hot_storage_path TEXT,
                s3_key TEXT,
                status_observer VARCHAR(32),
                status_converter VARCHAR(32),
                observer_failed_at TIMESTAMP,
                converter_failed_at TIMESTAMP,
                recording_start_time TIMESTAMP,
                recording_end_time TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                response_count INTEGER DEFAULT 0,
                UNIQUE(game_id, player_id)
            )
            """
        )

        # Maps table stores static map payloads uploaded to S3 (compressed with zstd).
        # Schema explanation:
        # - map_id: string identifier of the static map (primary key, unique across versions if map_id encodes version).
        # - s3_key: full S3 object key where the compressed payload is stored.
        # - created_at/updated_at: timestamps for bookkeeping.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS maps (
                id SERIAL PRIMARY KEY,
                map_id VARCHAR(40) NOT NULL UNIQUE,
                version VARCHAR(64),
                s3_key TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )

        # Games table stores per-game metadata shared between observer, converter, and API.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS games (
                id SERIAL PRIMARY KEY,
                game_id INTEGER NOT NULL UNIQUE,
                scenario_id INTEGER NOT NULL,
                discovered_date TIMESTAMP NOT NULL,
                started_date TIMESTAMP,
                completed_date TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )

        # Recording list table stores per-user recording preferences for games.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recording_list (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, game_id)
            )
            """
        )

        # Replay library table stores per-user references to completed game replays.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS replay_library (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, game_id)
            )
            """
        )

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
        
        # Upsert: observer may have already inserted (game_id, player_id) with status_converter NULL.
        cursor.execute("""
            INSERT INTO replays
            (game_id, player_id, replay_name, hot_storage_path, status_converter,
             recording_start_time, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_id, player_id) DO UPDATE SET
                replay_name = EXCLUDED.replay_name,
                hot_storage_path = EXCLUDED.hot_storage_path,
                status_converter = EXCLUDED.status_converter,
                recording_start_time = EXCLUDED.recording_start_time,
                updated_at = EXCLUDED.updated_at
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

    def get_observer_completed_pairs(
        self,
        game_player_pairs: Iterable[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """
        Given a set of (game_id, player_id) pairs, return those which the observer
        has marked as completed (status_observer = 'completed').
        """
        pairs = list(game_player_pairs)
        if not pairs:
            return []

        cursor = self.conn.cursor()

        # Build a safe IN clause for composite keys.
        # Example: WHERE (game_id, player_id) IN ((%s, %s), (%s, %s), ...)
        placeholders = ", ".join(["(%s, %s)"] * len(pairs))
        params: List[Any] = []
        for game_id, player_id in pairs:
            params.extend([int(game_id), int(player_id)])

        query = (
            "SELECT game_id, player_id FROM replays "
            f"WHERE (game_id, player_id) IN ({placeholders}) "
            "AND status_observer = %s"
        )
        params.append(ReplayStatus.COMPLETED.value)
        cursor.execute(query, params)
        return [(int(r["game_id"]), int(r["player_id"])) for r in cursor.fetchall()]
        
    def update_replay_status(
        self,
        replay_id: int,
        status: ReplayStatus,
        recording_end_time: Optional[datetime] = None,
        s3_key: Optional[str] = None,
    ):
        """
        Update the converter status of a replay (status_converter and converter_failed_at).
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        converter_failed_at = now if status.value == "failed" else None

        if recording_end_time and s3_key:
            query = self._format_query(
                """
                UPDATE replays
                SET status_converter = {}, recording_end_time = {},
                    s3_key = {}, converter_failed_at = {}, updated_at = {}
                WHERE id = {}
                """,
                6,
            )
            cursor.execute(
                query, (status.value, recording_end_time, s3_key, converter_failed_at, now, replay_id)
            )
        elif recording_end_time:
            query = self._format_query(
                """
                UPDATE replays
                SET status_converter = {}, recording_end_time = {}, converter_failed_at = {}, updated_at = {}
                WHERE id = {}
                """,
                5,
            )
            cursor.execute(query, (status.value, recording_end_time, converter_failed_at, now, replay_id))
        elif s3_key:
            query = self._format_query(
                """
                UPDATE replays
                SET status_converter = {}, s3_key = {}, converter_failed_at = {}, updated_at = {}
                WHERE id = {}
                """,
                5,
            )
            cursor.execute(query, (status.value, s3_key, converter_failed_at, now, replay_id))
        else:
            query = self._format_query(
                """
                UPDATE replays
                SET status_converter = {}, converter_failed_at = {}, updated_at = {}
                WHERE id = {}
                """,
                4,
            )
            cursor.execute(query, (status.value, converter_failed_at, now, replay_id))

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
            WHERE status_converter = {}
        """, 1)
        cursor.execute(query, (ReplayStatus.RECORDING.value,))
        
        return [dict(row) for row in cursor.fetchall()]

    def remove_game_from_recording_lists(self, game_id: int) -> None:
        """Remove a game from all users' recording lists."""
        cursor = self.conn.cursor()
        query = self._format_query("DELETE FROM recording_list WHERE game_id = {}", 1)
        cursor.execute(query, (game_id,))
        self.conn.commit()

    def is_conversion_failed(self, game_id: int, player_id: int) -> bool:
        """
        Check if this game/player is marked as conversion-failed (status_converter = 'failed').
        """
        cursor = self.conn.cursor()
        query = self._format_query(
            "SELECT 1 FROM replays WHERE game_id = {} AND player_id = {} AND status_converter = 'failed'",
            2,
        )
        cursor.execute(query, (game_id, player_id))
        return cursor.fetchone() is not None

    def record_conversion_failure(
        self, game_id: int, player_id: int, reason: Optional[str] = None
    ) -> None:
        """
        Record that we have given up converting this game/player (set status_converter = 'failed' on replays).
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        replay_name = f"game_{game_id}_player_{player_id}"
        cursor.execute(
            """
            INSERT INTO replays (game_id, player_id, replay_name, status_converter, converter_failed_at, created_at, updated_at)
            VALUES (%s, %s, %s, 'failed', %s, %s, %s)
            ON CONFLICT (game_id, player_id)
            DO UPDATE SET status_converter = 'failed', converter_failed_at = EXCLUDED.converter_failed_at, updated_at = EXCLUDED.updated_at
            """,
            (game_id, player_id, replay_name, now, now, now),
        )
        self.conn.commit()

    # --- Static maps helpers -------------------------------------------------
    def get_map_by_id(self, map_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a static map entry by its id.
        
        Args:
            map_id: Static map identifier
        
        Returns:
            Row dict or None if not found
        """
        cursor = self.conn.cursor()
        query = self._format_query("""
            SELECT * FROM maps
            WHERE map_id = {}
        """, 1)
        cursor.execute(query, (map_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_map_entry(self, map_id: int, s3_key: str, version: Optional[str] = None) -> int:
        """
        Create a new static map entry.
        The static map payload must be uploaded to S3 separately. This method only records metadata.
        
        Args:
            map_id: Static map identifier
            s3_key: Destination S3 object key
            version: Optional version string
        
        Returns:
            The ID of the created entry
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        cursor.execute(
            """
            INSERT INTO maps (map_id, version, s3_key, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (map_id, version, s3_key, now, now)
        )
        map_db_id = cursor.fetchone()['id']
        self.conn.commit()
        return map_db_id
