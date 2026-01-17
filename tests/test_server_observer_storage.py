"""
Tests for the ServerObserver storage with long-term storage feature.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.server_observer.storage import RecordingStorage


class TestRecordingStorageLongTermStorage(unittest.TestCase):
    """Test RecordingStorage class with long-term storage feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "output"
        self.lts_dir = Path(self.temp_dir) / "long_term_storage"
        
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_without_long_term_storage(self):
        """Test initialization without long-term storage."""
        storage = RecordingStorage(self.output_dir)
        self.assertTrue(storage.metadata_file.exists())
        self.assertIsNone(storage.long_term_storage_path)
        self.assertIsNone(storage.file_size_threshold)
        storage.teardown_logging()
    
    def test_init_with_long_term_storage(self):
        """Test initialization with long-term storage."""
        storage = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=1024
        )
        self.assertTrue(storage.metadata_file.exists())
        self.assertEqual(storage.long_term_storage_path, self.lts_dir)
        self.assertEqual(storage.file_size_threshold, 1024)
        storage.teardown_logging()
    
    def test_file_sequence_initialization(self):
        """Test that file sequence is initialized to 0."""
        storage = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=1024
        )
        self.assertEqual(storage._file_sequence, 0)
        storage.teardown_logging()
    
    def test_should_not_rotate_without_config(self):
        """Test that rotation doesn't happen without long-term storage config."""
        storage = RecordingStorage(self.output_dir)
        self.assertFalse(storage._should_rotate_file())
        storage.teardown_logging()
    
    def test_should_not_rotate_small_file(self):
        """Test that rotation doesn't happen for small files."""
        storage = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=1024 * 1024  # 1MB
        )
        # Create a small test file
        with open(storage.responses_file, 'w') as f:
            f.write("small content")
        
        self.assertFalse(storage._should_rotate_file())
        storage.teardown_logging()
    
    def test_should_rotate_large_file(self):
        """Test that rotation is triggered for large files."""
        storage = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=100  # 100 bytes
        )
        # Create a file larger than threshold
        with open(storage.responses_file, 'w') as f:
            f.write("x" * 200)
        
        self.assertTrue(storage._should_rotate_file())
        storage.teardown_logging()
    
    def test_rotate_to_long_term_storage(self):
        """Test file rotation to long-term storage."""
        storage = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=100
        )
        
        # Create a test file
        test_content = "x" * 200
        with open(storage.responses_file, 'w') as f:
            f.write(test_content)
        
        original_file = storage.responses_file
        self.assertTrue(original_file.exists())
        
        # Rotate the file
        storage._rotate_to_long_term_storage()
        
        # Check that original file is gone
        self.assertFalse(original_file.exists())
        
        # Check that file exists in long-term storage with correct structure
        game_dir_name = storage.output_path.name
        lts_game_dir = self.lts_dir / game_dir_name
        self.assertTrue(lts_game_dir.exists())
        
        # Check that rotated file exists with sequence number
        rotated_file = lts_game_dir / "responses_0001.jsonl.zst"
        self.assertTrue(rotated_file.exists())
        
        # Check metadata was updated
        metadata = storage._load_metadata()
        self.assertIn("rotations", metadata)
        self.assertEqual(len(metadata["rotations"]), 1)
        self.assertEqual(metadata["rotations"][0]["sequence"], 1)
        self.assertEqual(metadata["file_sequence"], 1)
        
        storage.teardown_logging()
    
    def test_multiple_rotations(self):
        """Test multiple file rotations increment sequence correctly."""
        storage = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=100
        )
        
        # First rotation
        with open(storage.responses_file, 'w') as f:
            f.write("x" * 200)
        storage._rotate_to_long_term_storage()
        
        # Second rotation
        with open(storage.responses_file, 'w') as f:
            f.write("y" * 200)
        storage._rotate_to_long_term_storage()
        
        # Third rotation
        with open(storage.responses_file, 'w') as f:
            f.write("z" * 200)
        storage._rotate_to_long_term_storage()
        
        # Check sequence number
        metadata = storage._load_metadata()
        self.assertEqual(metadata["file_sequence"], 3)
        self.assertEqual(len(metadata["rotations"]), 3)
        
        # Check all rotated files exist
        game_dir_name = storage.output_path.name
        lts_game_dir = self.lts_dir / game_dir_name
        self.assertTrue((lts_game_dir / "responses_0001.jsonl.zst").exists())
        self.assertTrue((lts_game_dir / "responses_0002.jsonl.zst").exists())
        self.assertTrue((lts_game_dir / "responses_0003.jsonl.zst").exists())
        
        storage.teardown_logging()
    
    def test_save_response_with_rotation(self):
        """Test that save_response rotates file when threshold is exceeded."""
        storage = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=100
        )
        
        # Create a large file that exceeds threshold
        with open(storage.responses_file, 'wb') as f:
            f.write(b"x" * 200)
        
        # Save a response - should trigger rotation
        test_response = {"test": "data", "large_field": "x" * 100}
        storage.save_response(test_response)
        
        # Check that rotation occurred
        game_dir_name = storage.output_path.name
        lts_game_dir = self.lts_dir / game_dir_name
        rotated_file = lts_game_dir / "responses_0001.jsonl.zst"
        self.assertTrue(rotated_file.exists())
        
        # New responses file should exist with the new response
        self.assertTrue(storage.responses_file.exists())
        
        storage.teardown_logging()
    
    def test_sequence_persistence(self):
        """Test that file sequence persists across storage instances."""
        # Create first storage instance and rotate a file
        storage1 = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=100
        )
        with open(storage1.responses_file, 'w') as f:
            f.write("x" * 200)
        storage1._rotate_to_long_term_storage()
        self.assertEqual(storage1._file_sequence, 1)
        storage1.teardown_logging()
        
        # Create second storage instance - should restore sequence
        storage2 = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=100
        )
        self.assertEqual(storage2._file_sequence, 1)
        
        # Rotate another file
        with open(storage2.responses_file, 'w') as f:
            f.write("y" * 200)
        storage2._rotate_to_long_term_storage()
        self.assertEqual(storage2._file_sequence, 2)
        storage2.teardown_logging()
    
    def test_validation_both_params_required(self):
        """Test that both long_term_storage_path and file_size_threshold must be provided together."""
        # Only long_term_storage_path provided - should raise error
        with self.assertRaises(ValueError) as context:
            RecordingStorage(
                self.output_dir,
                long_term_storage_path=self.lts_dir
            )
        self.assertIn("must be provided together", str(context.exception))
        
        # Only file_size_threshold provided - should raise error
        with self.assertRaises(ValueError) as context:
            RecordingStorage(
                self.output_dir,
                file_size_threshold=1024
            )
        self.assertIn("must be provided together", str(context.exception))
        
        # Both provided - should work
        storage = RecordingStorage(
            self.output_dir,
            long_term_storage_path=self.lts_dir,
            file_size_threshold=1024
        )
        storage.teardown_logging()
    
    def test_validation_positive_threshold(self):
        """Test that file_size_threshold must be positive."""
        with self.assertRaises(ValueError) as context:
            RecordingStorage(
                self.output_dir,
                long_term_storage_path=self.lts_dir,
                file_size_threshold=0
            )
        self.assertIn("must be positive", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            RecordingStorage(
                self.output_dir,
                long_term_storage_path=self.lts_dir,
                file_size_threshold=-100
            )
        self.assertIn("must be positive", str(context.exception))


if __name__ == '__main__':
    unittest.main()
