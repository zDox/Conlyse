"""
Tests for the Record to Replay Converter CLI tool.
"""
import os
import pickle
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import zstandard as zstd

from conflict_interface.replay.replay import Replay
from tools.record_to_replay.converter import RecordToReplayConverter


# Simple picklable state classes for testing
class PlayerState:
    """Simple player state mock for testing."""
    def __init__(self):
        self.player_id = 67890


class States:
    """Simple states container for testing."""
    def __init__(self):
        self.player_state = PlayerState()


class SimpleState:
    """Simple game state mock for testing."""
    def __init__(self):
        self.game_id = 12345
        self.player_id = 67890
        self.states = States()
        self.static_map_data = None
        self._game = None
    
    def set_game(self, game):
        """Set game reference (required by replay system)."""
        self._game = game


class TestRecordToReplayConverter(unittest.TestCase):
    """Test RecordToReplayConverter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.recording_dir = Path(self.temp_dir) / "recording"
        self.recording_dir.mkdir()
        
        # Create a mock game states file
        self.game_states_file = self.recording_dir / "game_states.bin"
        self._create_mock_recording()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_mock_recording(self):
        """Create a mock recording with sample game states."""
        compressor = zstd.ZstdCompressor(level=3)
        
        # Create simple mock game states using module-level class
        mock_states = []
        for i in range(3):
            state = SimpleState()
            mock_states.append(state)
        
        # Write to file
        with open(self.game_states_file, 'wb') as f:
            for i, state in enumerate(mock_states):
                timestamp_ms = 1000000000000 + (i * 60000)  # 1 minute apart
                
                # Pickle and compress
                state_bytes = pickle.dumps(state)
                compressed = compressor.compress(state_bytes)
                
                # Write timestamp, length, and data
                f.write(timestamp_ms.to_bytes(8, 'big'))
                f.write(len(compressed).to_bytes(4, 'big'))
                f.write(compressed)
    
    def test_init_with_valid_directory(self):
        """Test initialization with valid recording directory."""
        converter = RecordToReplayConverter(str(self.recording_dir))
        self.assertEqual(converter.recording_dir, self.recording_dir)
        self.assertTrue(converter.game_states_file.exists())
    
    def test_init_with_missing_directory(self):
        """Test initialization with missing directory."""
        with self.assertRaises(FileNotFoundError):
            RecordToReplayConverter("/nonexistent/directory")
    
    def test_init_with_missing_game_states_file(self):
        """Test initialization with missing game_states.bin file."""
        # Create directory without game states file
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()
        
        with self.assertRaises(FileNotFoundError):
            RecordToReplayConverter(str(empty_dir))
    
    def test_read_game_states(self):
        """Test reading game states from file."""
        converter = RecordToReplayConverter(str(self.recording_dir))
        game_states = converter._read_game_states()
        
        # Should read 3 states
        self.assertEqual(len(game_states), 3)
        
        # Check timestamps are sequential
        timestamps = [ts for ts, _ in game_states]
        self.assertEqual(len(timestamps), 3)
        self.assertTrue(all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1)))
    
    @patch('tools.record_to_replay.converter.make_bireplay_patch')
    def test_convert_success(self, mock_make_patch):
        """Test successful conversion."""
        # Mock the make_bireplay_patch function with proper patch objects
        mock_forward_patch = MagicMock()
        mock_forward_patch.to_bytes.return_value = b'forward_patch_bytes'
        mock_backward_patch = MagicMock()
        mock_backward_patch.to_bytes.return_value = b'backward_patch_bytes'
        
        mock_bipatch = MagicMock()
        mock_bipatch.forward_patch = mock_forward_patch
        mock_bipatch.backward_patch = mock_backward_patch
        mock_make_patch.return_value = mock_bipatch
        
        converter = RecordToReplayConverter(str(self.recording_dir))
        output_file = os.path.join(self.temp_dir, "test_replay.db")
        
        success = converter.convert(output_file)
        
        # Should succeed
        self.assertTrue(success)
        
        # Output file should exist
        self.assertTrue(os.path.exists(output_file))
        
        # Should have called make_bireplay_patch twice (for 3 states, 2 transitions)
        self.assertEqual(mock_make_patch.call_count, 2)
    
    def test_convert_with_explicit_ids(self):
        """Test conversion with explicit game and player IDs."""
        converter = RecordToReplayConverter(str(self.recording_dir))
        output_file = os.path.join(self.temp_dir, "test_replay2.db")
        
        with patch('tools.record_to_replay.converter.make_bireplay_patch') as mock_make_patch:
            # Mock with proper patch objects
            mock_forward_patch = MagicMock()
            mock_forward_patch.to_bytes.return_value = b'forward_patch_bytes'
            mock_backward_patch = MagicMock()
            mock_backward_patch.to_bytes.return_value = b'backward_patch_bytes'
            
            mock_bipatch = MagicMock()
            mock_bipatch.forward_patch = mock_forward_patch
            mock_bipatch.backward_patch = mock_backward_patch
            mock_make_patch.return_value = mock_bipatch
            
            success = converter.convert(
                output_file=output_file,
                game_id=99999,
                player_id=88888
            )
            
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_file))
    
    def test_convert_with_empty_recording(self):
        """Test conversion with empty recording."""
        # Create empty game states file
        empty_dir = Path(self.temp_dir) / "empty_recording"
        empty_dir.mkdir()
        empty_file = empty_dir / "game_states.bin"
        empty_file.touch()
        
        converter = RecordToReplayConverter(str(empty_dir))
        output_file = os.path.join(self.temp_dir, "test_replay_empty.db")
        
        success = converter.convert(output_file)
        
        # Should fail due to no game states
        self.assertFalse(success)


class TestRecordToReplayIntegration(unittest.TestCase):
    """Integration tests for the converter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('tools.record_to_replay.converter.make_bireplay_patch')
    def test_converted_replay_can_be_opened(self, mock_make_patch):
        """Test that converted replay can be opened and read."""
        # Mock with proper patch objects
        mock_forward_patch = MagicMock()
        mock_forward_patch.to_bytes.return_value = b'forward_patch_bytes'
        mock_backward_patch = MagicMock()
        mock_backward_patch.to_bytes.return_value = b'backward_patch_bytes'
        
        mock_bipatch = MagicMock()
        mock_bipatch.forward_patch = mock_forward_patch
        mock_bipatch.backward_patch = mock_backward_patch
        mock_make_patch.return_value = mock_bipatch
        
        # Create a mock recording
        recording_dir = Path(self.temp_dir) / "recording"
        recording_dir.mkdir()
        game_states_file = recording_dir / "game_states.bin"
        
        # Create simple mock states using module-level class
        compressor = zstd.ZstdCompressor(level=3)
        mock_state = SimpleState()
        
        with open(game_states_file, 'wb') as f:
            for i in range(2):
                timestamp_ms = 1000000000000 + (i * 60000)
                state_bytes = pickle.dumps(mock_state)
                compressed = compressor.compress(state_bytes)
                f.write(timestamp_ms.to_bytes(8, 'big'))
                f.write(len(compressed).to_bytes(4, 'big'))
                f.write(compressed)
        
        # Convert
        converter = RecordToReplayConverter(str(recording_dir))
        output_file = os.path.join(self.temp_dir, "test_replay.db")
        success = converter.convert(output_file)
        
        self.assertTrue(success)
        
        # Try to open the replay
        with Replay(filename=output_file, mode='r') as replay:
            # Should have metadata
            metadata = replay.get_metadata()
            self.assertEqual(metadata.game_id, 12345)
            self.assertEqual(metadata.player_id, 67890)
            
            # Should have timestamps
            timestamps = replay.get_timestamps()
            self.assertGreater(len(timestamps), 0)


if __name__ == '__main__':
    unittest.main()
