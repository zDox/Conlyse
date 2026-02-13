"""
Tests for the server converter database module.

NOTE: These tests require a PostgreSQL database to run.
To run tests, set up a test PostgreSQL instance and update the connection parameters below.
For CI/CD, consider using a PostgreSQL Docker container.

Example setup:
    docker run -d --name test-postgres \
        -e POSTGRES_DB=test_replays \
        -e POSTGRES_USER=test_user \
        -e POSTGRES_PASSWORD=test_pass \
        -p 5432:5432 \
        postgres:16-alpine

Then run: python -m unittest tests.test_server_converter_database
"""
import unittest
import os
from datetime import datetime

from tools.server_converter.database import ReplayDatabase, ReplayStatus

# Skip tests if PostgreSQL is not available
POSTGRES_AVAILABLE = os.getenv('TEST_POSTGRES_ENABLED', 'false').lower() == 'true'
POSTGRES_CONFIG = {
    'host': os.getenv('TEST_POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('TEST_POSTGRES_PORT', '5432')),
    'database': os.getenv('TEST_POSTGRES_DB', 'test_replays'),
    'user': os.getenv('TEST_POSTGRES_USER', 'test_user'),
    'password': os.getenv('TEST_POSTGRES_PASSWORD', 'test_pass'),
}


@unittest.skipUnless(POSTGRES_AVAILABLE, "PostgreSQL test database not available")
class TestReplayDatabasePostgreSQL(unittest.TestCase):
    """Test the ReplayDatabase class with PostgreSQL backend."""
    
    def setUp(self):
        """Create a test database connection."""
        self.db = ReplayDatabase(POSTGRES_CONFIG)
        try:
            self.db.connect()
            # Clean up any existing test data
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM replays")
            self.db.conn.commit()
        except Exception as e:
            self.skipTest(f"Cannot connect to PostgreSQL: {e}")
        
    def tearDown(self):
        """Close the database connection."""
        if self.db.conn:
            # Clean up test data
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM replays")
            self.db.conn.commit()
            self.db.close()
        
    def test_create_tables(self):
        """Test that tables are created successfully."""
        # Tables should be created in connect()
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'replays'
        """)
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result['table_name'], 'replays')
        
    def test_create_replay_entry(self):
        """Test creating a new replay entry."""
        replay_id = self.db.create_replay_entry(
            game_id=12345,
            player_id=67890,
            replay_name="test_replay",
            hot_storage_path="/path/to/replay.db"
        )
        
        self.assertIsNotNone(replay_id)
        self.assertGreater(replay_id, 0)
        
        # Verify the entry was created
        entry = self.db.get_replay_by_game_and_player(12345, 67890)
        self.assertIsNotNone(entry)
        self.assertEqual(entry['game_id'], 12345)
        self.assertEqual(entry['player_id'], 67890)
        self.assertEqual(entry['replay_name'], 'test_replay')
        self.assertEqual(entry['status'], ReplayStatus.RECORDING.value)
        
    def test_get_nonexistent_replay(self):
        """Test getting a replay that doesn't exist."""
        entry = self.db.get_replay_by_game_and_player(99999, 88888)
        self.assertIsNone(entry)
        
    def test_update_replay_status(self):
        """Test updating replay status."""
        # Create entry
        replay_id = self.db.create_replay_entry(
            game_id=12345,
            player_id=67890,
            replay_name="test_replay",
            hot_storage_path="/path/to/replay.db"
        )
        
        # Update status
        end_time = datetime.now()
        self.db.update_replay_status(
            replay_id,
            ReplayStatus.COMPLETED,
            recording_end_time=end_time
        )
        
        # Verify update
        entry = self.db.get_replay_by_game_and_player(12345, 67890)
        self.assertEqual(entry['status'], ReplayStatus.COMPLETED.value)
        self.assertIsNotNone(entry['recording_end_time'])
        
    def test_update_replay_status_with_cold_storage(self):
        """Test updating replay status with cold storage path."""
        # Create entry
        replay_id = self.db.create_replay_entry(
            game_id=12345,
            player_id=67890,
            replay_name="test_replay",
            hot_storage_path="/path/to/replay.db"
        )
        
        # Update with cold storage
        end_time = datetime.now()
        cold_path = "s3://bucket/replay.db"
        self.db.update_replay_status(
            replay_id,
            ReplayStatus.ARCHIVED,
            recording_end_time=end_time,
            cold_storage_path=cold_path
        )
        
        # Verify update
        entry = self.db.get_replay_by_game_and_player(12345, 67890)
        self.assertEqual(entry['status'], ReplayStatus.ARCHIVED.value)
        self.assertEqual(entry['cold_storage_path'], cold_path)
        
    def test_increment_response_count(self):
        """Test incrementing response count."""
        # Create entry
        replay_id = self.db.create_replay_entry(
            game_id=12345,
            player_id=67890,
            replay_name="test_replay",
            hot_storage_path="/path/to/replay.db"
        )
        
        # Increment count
        self.db.increment_response_count(replay_id, 10)
        
        # Verify
        entry = self.db.get_replay_by_game_and_player(12345, 67890)
        self.assertEqual(entry['response_count'], 10)
        
        # Increment again
        self.db.increment_response_count(replay_id, 5)
        entry = self.db.get_replay_by_game_and_player(12345, 67890)
        self.assertEqual(entry['response_count'], 15)
        
    def test_get_all_active_replays(self):
        """Test getting all active replays."""
        # Create multiple entries
        self.db.create_replay_entry(12345, 67890, "replay1", "/path1")
        self.db.create_replay_entry(12346, 67891, "replay2", "/path2")
        
        replay_id3 = self.db.create_replay_entry(12347, 67892, "replay3", "/path3")
        
        # Mark one as completed
        self.db.update_replay_status(replay_id3, ReplayStatus.COMPLETED)
        
        # Get active replays
        active = self.db.get_all_active_replays()
        self.assertEqual(len(active), 2)
        
        # Verify they're all recording status
        for entry in active:
            self.assertEqual(entry['status'], ReplayStatus.RECORDING.value)


if __name__ == '__main__':
    unittest.main()
