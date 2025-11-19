"""Tests for the Replay Debug CLI tool."""
import unittest
import sys
import io
from unittest.mock import Mock, patch
from datetime import datetime, UTC

from tools.replay_debug import ReplayDebugCLI
from conflict_interface.replay.replay_patch import ReplayPatch, AddOperation, ReplaceOperation, RemoveOperation


class TestReplayDebugCLI(unittest.TestCase):
    """Test cases for the ReplayDebugCLI class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cli = ReplayDebugCLI("test_replay.db")
    
    def test_init(self):
        """Test CLI initialization."""
        self.assertEqual(self.cli.filename, "test_replay.db")
        self.assertIsNone(self.cli.replay)
    
    def test_path_starts_with_empty_prefix(self):
        """Test path matching with empty prefix."""
        path = ["states", "map_state", "provinces"]
        prefix = []
        self.assertTrue(self.cli._path_starts_with(path, prefix))
    
    def test_path_starts_with_matching_prefix(self):
        """Test path matching with matching prefix."""
        path = ["states", "map_state", "provinces", "1"]
        prefix = ["states", "map_state"]
        self.assertTrue(self.cli._path_starts_with(path, prefix))
    
    def test_path_starts_with_non_matching_prefix(self):
        """Test path matching with non-matching prefix."""
        path = ["states", "player_state", "resources"]
        prefix = ["states", "map_state"]
        self.assertFalse(self.cli._path_starts_with(path, prefix))
    
    def test_path_starts_with_prefix_too_long(self):
        """Test path matching when prefix is longer than path."""
        path = ["states"]
        prefix = ["states", "map_state", "provinces"]
        self.assertFalse(self.cli._path_starts_with(path, prefix))
    
    @patch('conflict_interface.cli.replay_debug.cli.Replay')
    def test_open_replay_success(self, mock_replay_class):
        """Test successfully opening a replay."""
        mock_replay = Mock()
        mock_replay.db.read_patches.return_value = {}
        mock_replay_class.return_value = mock_replay
        
        result = self.cli.open_replay()
        
        self.assertTrue(result)
        mock_replay_class.assert_called_once_with("test_replay.db", 'r')
        mock_replay.open.assert_called_once()
    
    @patch('conflict_interface.cli.replay_debug.cli.Replay')
    def test_open_replay_file_not_found(self, mock_replay_class):
        """Test opening a non-existent replay file."""
        mock_replay_class.side_effect = FileNotFoundError()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        result = self.cli.open_replay()
        
        sys.stdout = sys.__stdout__
        
        self.assertFalse(result)
        self.assertIn("not found", captured_output.getvalue())
    
    @patch('conflict_interface.cli.replay_debug.cli.Replay')
    def test_list_patches(self, mock_replay_class):
        """Test listing patches."""
        # Setup mock replay
        mock_replay = Mock()
        mock_replay.start_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        mock_replay.last_time = datetime(2023, 1, 1, 0, 2, 0, tzinfo=UTC)
        
        # Create test patches
        patch1 = ReplayPatch()
        patch1.add_op(["test"], "value1")
        patch2 = ReplayPatch()
        patch2.replace_op(["test"], "value2")
        
        mock_replay.db.read_patches.return_value = {
            (1672531200000, 1672531260000): patch1,
            (1672531260000, 1672531200000): patch2,
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.list_patches()
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("Total patches: 2", output)
        self.assertIn("test_replay.db", output)
        self.assertIn("Forward", output)
        self.assertIn("Backward", output)
    
    def test_count_operations_no_replay(self):
        """Test counting operations when replay is not opened."""
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.count_operations()
        
        sys.stdout = sys.__stdout__
        
        self.assertIn("Error: Replay not opened", captured_output.getvalue())
    
    def test_view_operations_by_path(self):
        """Test viewing operations by path prefix."""
        # Setup mock replay with patches
        mock_replay = Mock()
        
        # Create test patches with different paths
        patch1 = ReplayPatch()
        patch1.add_op(["states", "map_state", "province", "1"], "province_1")
        patch1.replace_op(["states", "player_state", "gold"], 100)
        
        patch2 = ReplayPatch()
        patch2.add_op(["states", "map_state", "province", "2"], "province_2")
        patch2.replace_op(["game_info", "turn"], 1)
        
        mock_replay.db.read_patches.return_value = {
            (1000, 2000): patch1,
            (2000, 1000): patch2,
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.view_operations_by_path("states/map_state", limit=10)
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("states/map_state", output)
        self.assertIn("Total matching operations: 2", output)
    
    def test_count_operations_by_path_with_forward_backward(self):
        """Test counting operations by path with forward and backward patches."""
        # Setup mock replay
        mock_replay = Mock()
        
        # Create forward and backward patches
        forward_patch = ReplayPatch()
        forward_patch.add_op(["states", "map_state", "data"], "value1")
        forward_patch.replace_op(["states", "player_state", "gold"], 100)
        
        backward_patch = ReplayPatch()
        backward_patch.remove_op(["states", "map_state", "data"])
        backward_patch.replace_op(["states", "player_state", "gold"], 0)
        
        mock_replay.db.read_patches.return_value = {
            (1000, 2000): forward_patch,  # Forward
            (2000, 1000): backward_patch,  # Backward
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.count_operations_by_path("states/map_state")
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("Matching operations: 2", output)
        self.assertIn("In forward patches:  1", output)
        self.assertIn("In backward patches: 1", output)
    
    def test_view_operations_by_path_forward_only(self):
        """Test viewing operations by path with forward-only filter."""
        # Setup mock replay with patches
        mock_replay = Mock()
        
        # Create test patches with different paths
        patch1 = ReplayPatch()
        patch1.add_op(["states", "map_state", "province", "1"], "province_1")
        
        patch2 = ReplayPatch()
        patch2.remove_op(["states", "map_state", "province", "1"])
        
        mock_replay.db.read_patches.return_value = {
            (1000, 2000): patch1,  # Forward
            (2000, 1000): patch2,  # Backward
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.view_operations_by_path("states/map_state", limit=10, direction='forward')
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("forward patches only", output)
        self.assertIn("Total matching operations: 1", output)
    
    def test_view_operations_by_path_backward_only(self):
        """Test viewing operations by path with backward-only filter."""
        # Setup mock replay with patches
        mock_replay = Mock()
        
        # Create test patches with different paths
        patch1 = ReplayPatch()
        patch1.add_op(["states", "map_state", "province", "1"], "province_1")
        
        patch2 = ReplayPatch()
        patch2.remove_op(["states", "map_state", "province", "1"])
        
        mock_replay.db.read_patches.return_value = {
            (1000, 2000): patch1,  # Forward
            (2000, 1000): patch2,  # Backward
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.view_operations_by_path("states/map_state", limit=10, direction='backward')
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("backward patches only", output)
        self.assertIn("Total matching operations: 1", output)
    
    def test_operations_overview(self):
        """Test operations overview grouped by state."""
        # Setup mock replay
        mock_replay = Mock()
        
        # Create patches with different states
        patch1 = ReplayPatch()
        patch1.add_op(["states", "map_state", "data"], "value1")
        patch1.replace_op(["states", "player_state", "gold"], 100)
        patch1.remove_op(["game_info", "old"])
        
        patch2 = ReplayPatch()
        patch2.add_op(["states", "map_state", "data2"], "value2")
        
        mock_replay.db.read_patches.return_value = {
            (1000, 2000): patch1,
            (2000, 3000): patch2,
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.operations_overview(direction='both')
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("Operations Overview", output)
        self.assertIn("states/map_state", output)
        self.assertIn("states/player_state", output)
        self.assertIn("game_info", output)
        self.assertIn("TOTAL", output)
    
    @patch('conflict_interface.cli.replay_debug.cli.Replay')
    def test_view_patch_with_limit(self, mock_replay_class):
        """Test viewing a patch with a limit parameter."""
        # Setup mock replay
        mock_replay = Mock()
        
        # Create a patch with multiple operations
        patch = ReplayPatch()
        for i in range(10):
            patch.add_op(["states", "test", str(i)], f"value_{i}")
        
        mock_replay.db.read_patches.return_value = {
            (1000, 2000): patch,
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.view_patch_by_index(1, limit=5)
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("Showing first 5 operations", output)
        self.assertIn("and 5 more operations", output)
    
    @patch('conflict_interface.cli.replay_debug.cli.Replay')
    def test_display_metadata(self, mock_replay_class):
        """Test displaying replay metadata."""
        # Setup mock replay
        mock_replay = Mock()
        mock_replay.get_metadata.return_value = Mock(
            version=206,
            game_id=12345,
            player_id=67890,
            start_time=1672531200000,
            last_time=1672531800000
        )
        mock_replay.db.read_patches.return_value = {
            (1000, 2000): ReplayPatch(),
            (2000, 1000): ReplayPatch(),
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.display_metadata()
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        self.assertIn("Replay Metadata", output)
        self.assertIn("Version:     206", output)
        self.assertIn("Game ID:     12345", output)
        self.assertIn("Player ID:   67890", output)
        self.assertIn("Duration:", output)
        self.assertIn("10.00 minutes", output)
    
    @patch('conflict_interface.cli.replay_debug.cli.Replay')
    def test_view_patch_shows_before_after_values(self, mock_replay_class):
        """Test that view patch shows before and after values."""
        # Setup mock replay
        mock_replay = Mock()
        
        # Create forward and backward patches
        forward_patch = ReplayPatch()
        forward_patch.replace_op(["states", "gold"], 1500)
        forward_patch.add_op(["states", "turn"], 1)
        
        backward_patch = ReplayPatch()
        backward_patch.replace_op(["states", "gold"], 1000)  # old value
        backward_patch.remove_op(["states", "turn"])
        
        mock_replay.db.read_patches.return_value = {
            (1000, 2000): forward_patch,
            (2000, 1000): backward_patch,
        }
        
        self.cli.replay = mock_replay
        self.cli._load_all_patches()
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.cli.view_patch_by_index(1)
        
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        # Should show before and after columns
        self.assertIn("Before", output)
        self.assertIn("After", output)
        # For replace operation, should show old value (1000) and new value (1500)
        self.assertIn("1000", output)
        self.assertIn("1500", output)
        # For add operation, should show <not set>
        self.assertIn("<not set>", output)


class TestReplayPatchOperations(unittest.TestCase):
    """Test replay patch operations for the CLI."""
    
    def test_create_patch_with_operations(self):
        """Test creating a patch with different operation types."""
        patch = ReplayPatch()
        
        patch.add_op(["test", "add"], "new_value")
        patch.replace_op(["test", "replace"], "updated_value")
        patch.remove_op(["test", "remove"])
        
        self.assertEqual(len(patch.operations), 3)
        self.assertIsInstance(patch.operations[0], AddOperation)
        self.assertIsInstance(patch.operations[1], ReplaceOperation)
        self.assertIsInstance(patch.operations[2], RemoveOperation)
    
    def test_patch_serialization(self):
        """Test patch to/from bytes serialization."""
        patch = ReplayPatch()
        patch.add_op(["states", "test"], 42)
        patch.replace_op(["states", "counter"], 100)
        
        # Serialize and deserialize
        serialized = patch.to_bytes()
        deserialized = ReplayPatch.from_bytes(serialized)
        
        self.assertEqual(len(deserialized.operations), 2)
        self.assertEqual(deserialized.operations[0].path, ["states", "test"])
        self.assertEqual(deserialized.operations[0].new_value, 42)


if __name__ == '__main__':
    unittest.main()
