"""
Tests for the server converter database module.
"""
import unittest
import tempfile
from pathlib import Path
from datetime import datetime

from tools.server_converter.database import ReplayDatabase, ReplayStatus


class TestReplayDatabaseSQLite(unittest.TestCase):
    """Test the ReplayDatabase class with SQLite backend."""
    
    def setUp(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_replays.db"
        self.db = ReplayDatabase(self.db_path)
        self.db.connect()
        
    def tearDown(self):
        """Close the database and clean up."""
        self.db.close()
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_create_tables(self):
        """Test that tables are created successfully."""
        # Tables should be created in connect()
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='replays'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'replays')
        
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
