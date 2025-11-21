"""Tests for the enhanced replay debug CLI features."""
import unittest
import sys
import io
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, UTC

from tools.replay_debug import ReplayDebugCLI, ReplayNavigator, StateViewer


class TestReplayNavigator(unittest.TestCase):
    """Test cases for the ReplayNavigator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ritf = Mock()
        self.mock_ritf.current_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        self.mock_ritf.start_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        self.mock_ritf.end_time = datetime(2023, 1, 1, 23, 59, 59, tzinfo=UTC)
        self.mock_ritf.current_timestamp_index = 50
        self.mock_ritf.jump_to = Mock()
        self.mock_ritf.jump_to_next_patch = Mock(return_value=True)
        self.mock_ritf.jump_to_previous_patch = Mock(return_value=True)
        
        # Create a list of timestamps
        timestamps = []
        for i in range(100):
            timestamps.append(datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(minutes=i*10))
        self.mock_ritf.get_timestamps = Mock(return_value=timestamps)
        
        self.navigator = ReplayNavigator(self.mock_ritf)
    
    def test_jump_by_relative_time_forward(self):
        """Test jumping forward by relative time."""
        result = self.navigator.jump_by_relative_time(60)
        
        self.assertTrue(result)
        self.mock_ritf.jump_to.assert_called_once()
        # Should jump to 12:01:00
        call_args = self.mock_ritf.jump_to.call_args[0][0]
        expected = datetime(2023, 1, 1, 12, 1, 0, tzinfo=UTC)
        self.assertEqual(call_args, expected)
    
    def test_jump_by_relative_time_backward(self):
        """Test jumping backward by relative time."""
        result = self.navigator.jump_by_relative_time(-60)
        
        self.assertTrue(result)
        self.mock_ritf.jump_to.assert_called_once()
        # Should jump to 11:59:00
        call_args = self.mock_ritf.jump_to.call_args[0][0]
        expected = datetime(2023, 1, 1, 11, 59, 0, tzinfo=UTC)
        self.assertEqual(call_args, expected)
    
    def test_jump_by_relative_time_clamps_to_start(self):
        """Test that jumping backward clamps to start time."""
        result = self.navigator.jump_by_relative_time(-100000)
        
        self.assertTrue(result)
        self.mock_ritf.jump_to.assert_called_once()
        # Should clamp to start time
        call_args = self.mock_ritf.jump_to.call_args[0][0]
        self.assertEqual(call_args, self.mock_ritf.start_time)
    
    def test_jump_by_relative_time_clamps_to_end(self):
        """Test that jumping forward clamps to end time."""
        result = self.navigator.jump_by_relative_time(100000)
        
        self.assertTrue(result)
        self.mock_ritf.jump_to.assert_called_once()
        # Should clamp to end time
        call_args = self.mock_ritf.jump_to.call_args[0][0]
        self.assertEqual(call_args, self.mock_ritf.end_time)
    
    def test_jump_to_absolute_time(self):
        """Test jumping to an absolute timestamp."""
        target = datetime(2023, 1, 1, 15, 30, 0, tzinfo=UTC)
        result = self.navigator.jump_to_absolute_time(target)
        
        self.assertTrue(result)
        self.mock_ritf.jump_to.assert_called_once_with(target)
    
    def test_jump_by_patches_forward(self):
        """Test jumping forward by patches."""
        result = self.navigator.jump_by_patches(5)
        
        self.assertTrue(result)
        self.assertEqual(self.mock_ritf.jump_to_next_patch.call_count, 5)
    
    def test_jump_by_patches_backward(self):
        """Test jumping backward by patches."""
        result = self.navigator.jump_by_patches(-3)
        
        self.assertTrue(result)
        self.assertEqual(self.mock_ritf.jump_to_previous_patch.call_count, 3)
    
    def test_jump_by_patches_zero(self):
        """Test jumping by zero patches."""
        result = self.navigator.jump_by_patches(0)
        
        self.assertTrue(result)
        self.mock_ritf.jump_to_next_patch.assert_not_called()
        self.mock_ritf.jump_to_previous_patch.assert_not_called()
    
    def test_jump_to_timestamp_index(self):
        """Test jumping to a timestamp by index."""
        result = self.navigator.jump_to_timestamp_index(42)
        
        self.assertTrue(result)
        timestamps = self.mock_ritf.get_timestamps()
        self.mock_ritf.jump_to.assert_called_once_with(timestamps[42])
    
    def test_jump_to_timestamp_index_out_of_range(self):
        """Test jumping to invalid index."""
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        result = self.navigator.jump_to_timestamp_index(1000)
        
        sys.stdout = sys.__stdout__
        
        self.assertFalse(result)
        self.assertIn("out of range", captured_output.getvalue())
    
    def test_list_timestamps(self):
        """Test listing timestamps."""
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.navigator.list_timestamps(limit=10)
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("Total timestamps: 100", output)
        self.assertIn("Current index: 50", output)
        self.assertIn("Index", output)
        self.assertIn("Timestamp", output)
    
    def test_get_current_position_info(self):
        """Test getting current position information."""
        idx, current, start, end = self.navigator.get_current_position_info()
        
        self.assertEqual(idx, 50)
        self.assertEqual(current, datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC))
        self.assertEqual(start, datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC))
        self.assertEqual(end, datetime(2023, 1, 1, 23, 59, 59, tzinfo=UTC))


class TestStateViewer(unittest.TestCase):
    """Test cases for the StateViewer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ritf = MagicMock()
        # Create a simple game state structure
        self.mock_ritf.game_state = MagicMock()
        self.state_viewer = StateViewer(self.mock_ritf)
    
    def test_list_available_states_no_game_state(self):
        """Test listing states when game state is not loaded."""
        self.mock_ritf.game_state = None
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.state_viewer.list_available_states()
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("Error: Game state not loaded", output)
    
    def test_pretty_print_basic_types(self):
        """Test pretty printing of basic types."""
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.state_viewer._pretty_print_value(42)
        self.state_viewer._pretty_print_value("test string")
        self.state_viewer._pretty_print_value(True)
        self.state_viewer._pretty_print_value(None)
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("42", output)
        self.assertIn("test string", output)
        self.assertIn("True", output)
        self.assertIn("None", output)
    
    def test_pretty_print_list(self):
        """Test pretty printing of lists."""
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.state_viewer._pretty_print_value([1, 2, 3])
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("[", output)
        self.assertIn("]", output)
        self.assertIn("[0]: 1", output)
        self.assertIn("[1]: 2", output)
    
    def test_pretty_print_dict(self):
        """Test pretty printing of dicts."""
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.state_viewer._pretty_print_value({"key1": "value1", "key2": 42})
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("{", output)
        self.assertIn("}", output)
        self.assertIn("key1: value1", output)
        self.assertIn("key2: 42", output)
    
    def test_pretty_print_max_depth(self):
        """Test that max depth is respected."""
        # Create deeply nested structure
        nested = {"level1": {"level2": {"level3": {"level4": {"level5": {"level6": "deep"}}}}}}
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.state_viewer._pretty_print_value(nested, max_depth=3)
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("max depth reached", output)


class TestReplayDebugCLI(unittest.TestCase):
    """Test cases for the ReplayDebugCLI class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cli = ReplayDebugCLI("test_replay.db")
    
    def test_init(self):
        """Test CLI initialization."""
        self.assertEqual(self.cli.filename, "test_replay.db")
        self.assertIsNone(self.cli.ritf)
        self.assertIsNone(self.cli.navigator)
        self.assertIsNone(self.cli.state_viewer)
    
    @patch('tools.replay_debug.cli.ReplayInterface')
    def test_open_replay_success(self, mock_ritf_class):
        """Test successfully opening a replay."""
        mock_ritf = Mock()
        mock_ritf_class.return_value = mock_ritf
        
        result = self.cli.open_replay()
        
        self.assertTrue(result)
        mock_ritf_class.assert_called_once_with("test_replay.db")
        mock_ritf.open.assert_called_once()
        self.assertIsNotNone(self.cli.ritf)
        self.assertIsNotNone(self.cli.navigator)
        self.assertIsNotNone(self.cli.state_viewer)
    
    @patch('tools.replay_debug.cli.ReplayInterface')
    def test_open_replay_file_not_found(self, mock_ritf_class):
        """Test opening a non-existent replay file."""
        mock_ritf_class.side_effect = FileNotFoundError()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        result = self.cli.open_replay()
        
        sys.stdout = sys.__stdout__
        
        self.assertFalse(result)
        self.assertIn("not found", captured_output.getvalue())
    
    def test_get_ritf(self):
        """Test getting the RITF instance."""
        self.assertIsNone(self.cli.get_ritf())
        
        # Set up a mock ritf
        mock_ritf = Mock()
        self.cli.ritf = mock_ritf
        
        self.assertEqual(self.cli.get_ritf(), mock_ritf)
    
    @patch('tools.replay_debug.cli.ReplayInterface')
    def test_display_info(self, mock_ritf_class):
        """Test displaying replay info."""
        # Setup mock
        mock_ritf = Mock()
        mock_ritf.game_id = 12345
        mock_ritf.player_id = 67890
        mock_ritf.current_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_ritf.start_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        mock_ritf.end_time = datetime(2023, 1, 1, 23, 59, 59, tzinfo=UTC)
        mock_ritf.current_timestamp_index = 50
        mock_ritf.get_timestamps = Mock(return_value=[datetime(2023, 1, 1, i, 0, 0, tzinfo=UTC) for i in range(24)])
        
        self.cli.ritf = mock_ritf
        self.cli.navigator = ReplayNavigator(mock_ritf)
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.display_info()
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("Replay Information", output)
        self.assertIn("12345", output)
        self.assertIn("67890", output)
        self.assertIn("Current Position", output)


if __name__ == '__main__':
    unittest.main()
