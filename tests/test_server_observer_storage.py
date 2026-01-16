"""
Unit tests for ServerObserver storage module with separate metadata and response directories.
"""
import json
import tempfile
import unittest
from pathlib import Path

from tools.server_observer.storage import RecordingStorage


class TestRecordingStorageSeparateDirectories(unittest.TestCase):
    """Test RecordingStorage with separate metadata and response directories."""

    def setUp(self):
        """Create temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.responses_dir = Path(self.temp_dir) / "responses"
        self.metadata_dir = Path(self.temp_dir) / "metadata"

    def test_separate_directories_for_metadata_and_responses(self):
        """Test that metadata and responses are stored in separate directories."""
        # Create storage with separate directories
        storage = RecordingStorage(
            output_path=self.responses_dir,
            metadata_path=self.metadata_dir
        )

        # Check that directories were created
        self.assertTrue(self.responses_dir.exists())
        self.assertTrue(self.metadata_dir.exists())

        # Check that response files are in responses directory
        self.assertEqual(storage.responses_file.parent, self.responses_dir)
        self.assertEqual(storage.requests_file.parent, self.responses_dir)
        self.assertEqual(storage.game_states_file.parent, self.responses_dir)
        self.assertEqual(storage.static_map_data_file.parent, self.responses_dir)

        # Check that metadata files are in metadata directory
        self.assertEqual(storage.metadata_file.parent, self.metadata_dir)
        self.assertEqual(storage.recorder_log_file.parent, self.metadata_dir)
        self.assertEqual(storage.library_log_file.parent, self.metadata_dir)

        # Verify metadata file was created in the correct location
        self.assertTrue(storage.metadata_file.exists())
        self.assertTrue((self.metadata_dir / "metadata.json").exists())

    def test_same_directory_when_metadata_path_not_specified(self):
        """Test backward compatibility when metadata_path is not specified."""
        # Create storage without separate metadata directory
        storage = RecordingStorage(output_path=self.responses_dir)

        # Check that both response and metadata files are in the same directory
        self.assertEqual(storage.responses_file.parent, self.responses_dir)
        self.assertEqual(storage.metadata_file.parent, self.responses_dir)
        self.assertEqual(storage.recorder_log_file.parent, self.responses_dir)

    def test_save_response_to_separate_directory(self):
        """Test that responses are saved to the responses directory."""
        storage = RecordingStorage(
            output_path=self.responses_dir,
            metadata_path=self.metadata_dir
        )

        # Save a test response
        test_response = {"result": {"test": "data"}}
        storage.save_response(test_response)

        # Verify response file is in responses directory
        self.assertTrue(storage.responses_file.exists())
        self.assertEqual(storage.responses_file.parent, self.responses_dir)

        # Verify metadata is in metadata directory
        self.assertTrue(storage.metadata_file.exists())
        self.assertEqual(storage.metadata_file.parent, self.metadata_dir)

        # Verify metadata was updated with timestamp
        with open(storage.metadata_file, 'r') as f:
            metadata = json.load(f)
        self.assertIn("updates", metadata)
        self.assertEqual(len(metadata["updates"]), 1)

    def test_resume_metadata_in_metadata_directory(self):
        """Test that resume metadata is saved in the metadata directory."""
        storage = RecordingStorage(
            output_path=self.responses_dir,
            metadata_path=self.metadata_dir
        )

        # Update resume metadata
        test_resume_data = {
            "game_id": 12345,
            "auth": {"token": "test_token"}
        }
        storage.update_resume_metadata(test_resume_data)

        # Verify metadata file is in metadata directory
        self.assertTrue(storage.metadata_file.exists())
        self.assertEqual(storage.metadata_file.parent, self.metadata_dir)

        # Verify resume data was saved
        with open(storage.metadata_file, 'r') as f:
            metadata = json.load(f)
        self.assertIn("resume", metadata)
        self.assertEqual(metadata["resume"], test_resume_data)

        # Verify it can be retrieved
        retrieved_resume = storage.get_resume_metadata()
        self.assertEqual(retrieved_resume, test_resume_data)


if __name__ == '__main__':
    unittest.main()
