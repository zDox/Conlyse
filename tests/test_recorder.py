"""
Tests for the Recorder CLI tool.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

from conflict_interface.cli.recorder.config_schema import (
    BuildUpgradeAction,
    MobilizeUnitAction,
    RecorderConfig,
    SleepAction,
    SleepWithUpdatesAction,
    ArmyMoveAction,
)
from conflict_interface.cli.recorder.recorder import Recorder, RecordingStorage


class TestRecordingStorage(unittest.TestCase):
    """Test RecordingStorage class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = RecordingStorage(self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_creates_files(self):
        """Test that initialization creates necessary files."""
        self.assertTrue(self.storage.metadata_file.exists())
        
        # Check metadata content
        metadata = self.storage._load_metadata()
        self.assertIn('version', metadata)
        self.assertIn('created_at', metadata)
        self.assertIn('updates', metadata)
    
    def test_save_update(self):
        """Test saving an update."""
        mock_game_state = {"test": "state"}
        mock_response = {"result": "ok"}
        timestamp = 1234567890.0
        
        self.storage.save_update(mock_game_state, mock_response, timestamp)
        
        # Check that files were created
        self.assertTrue(self.storage.game_states_file.exists())
        self.assertTrue(self.storage.responses_file.exists())
        
        # Check metadata was updated
        metadata = self.storage._load_metadata()
        self.assertEqual(len(metadata['updates']), 1)
        self.assertEqual(metadata['updates'][0]['timestamp'], timestamp)


class TestRecorderConfig(unittest.TestCase):
    """Test configuration schema."""
    
    def test_build_upgrade_action(self):
        """Test BuildUpgradeAction creation."""
        action = BuildUpgradeAction(
            city_name="Washington",
            building_name="Arms Industry",
            tier=1
        )
        self.assertEqual(action.type, "build_upgrade")
        self.assertEqual(action.city_name, "Washington")
        self.assertEqual(action.tier, 1)
    
    def test_sleep_action(self):
        """Test SleepAction creation."""
        action = SleepAction(duration=10, unit="minutes")
        self.assertEqual(action.type, "sleep")
        self.assertEqual(action.duration, 10)
        self.assertEqual(action.unit, "minutes")
    
    def test_recorder_config(self):
        """Test RecorderConfig creation."""
        config = RecorderConfig(
            username="test",
            password="pass",
            scenario_id=5975,
            actions=[]
        )
        self.assertEqual(config.username, "test")
        self.assertEqual(config.scenario_id, 5975)
        self.assertIsNotNone(config.actions)


class TestRecorder(unittest.TestCase):
    """Test Recorder class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'username': 'test_user',
            'password': 'test_pass',
            'scenario_id': 5975,
            'output_dir': '/tmp/test_recordings',
            'actions': []
        }
        self.recorder = Recorder(self.config)
    
    def test_init(self):
        """Test recorder initialization."""
        self.assertIsNone(self.recorder.interface)
        self.assertIsNone(self.recorder.game)
        self.assertIsNone(self.recorder.storage)
        self.assertEqual(self.recorder.config, self.config)
    
    @patch('conflict_interface.cli.recorder.recorder.RecordingStorage')
    def test_setup_storage(self, mock_storage_class):
        """Test storage setup."""
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        
        self.recorder._setup_storage()
        
        self.assertIsNotNone(self.recorder.storage)
        mock_storage_class.assert_called_once()
    
    @patch('conflict_interface.cli.recorder.recorder.HubInterface')
    def test_login_success(self, mock_hub_interface):
        """Test successful login."""
        mock_interface = MagicMock()
        mock_hub_interface.return_value = mock_interface
        
        result = self.recorder.login()
        
        self.assertTrue(result)
        mock_interface.login.assert_called_once_with('test_user', 'test_pass')
    
    @patch('conflict_interface.cli.recorder.recorder.HubInterface')
    def test_login_failure(self, mock_hub_interface):
        """Test login failure."""
        mock_interface = MagicMock()
        mock_interface.login.side_effect = Exception("Login failed")
        mock_hub_interface.return_value = mock_interface
        
        result = self.recorder.login()
        
        self.assertFalse(result)
    
    def test_execute_action_unknown_type(self):
        """Test execution of unknown action type."""
        self.recorder.game = MagicMock()
        
        action = {'type': 'unknown_action'}
        result = self.recorder.execute_action(action)
        
        self.assertFalse(result)
    
    def test_execute_action_no_type(self):
        """Test execution of action without type."""
        action = {}
        result = self.recorder.execute_action(action)
        
        self.assertFalse(result)
    
    @patch.object(Recorder, '_build_upgrade')
    def test_execute_action_build_upgrade(self, mock_build):
        """Test execution of build_upgrade action."""
        mock_build.return_value = True
        self.recorder.game = MagicMock()
        
        action = {'type': 'build_upgrade', 'city_name': 'Test'}
        result = self.recorder.execute_action(action)
        
        self.assertTrue(result)
        mock_build.assert_called_once_with(action)
    
    @patch.object(Recorder, '_sleep')
    def test_execute_action_sleep(self, mock_sleep):
        """Test execution of sleep action."""
        mock_sleep.return_value = True
        
        action = {'type': 'sleep', 'duration': 10}
        result = self.recorder.execute_action(action)
        
        self.assertTrue(result)
        mock_sleep.assert_called_once_with(action)
    
    def test_get_army_by_id(self):
        """Test getting army by ID."""
        mock_game = MagicMock()
        mock_army = MagicMock()
        mock_game.get_army.return_value = mock_army
        self.recorder.game = mock_game
        
        action = {'army_id': 123}
        army = self.recorder._get_army(action)
        
        self.assertEqual(army, mock_army)
        mock_game.get_army.assert_called_once_with(123)
    
    def test_get_army_by_number(self):
        """Test getting army by number."""
        mock_game = MagicMock()
        mock_army = MagicMock()
        mock_game.get_my_army_by_number.return_value = mock_army
        self.recorder.game = mock_game
        
        action = {'army_number': 5}
        army = self.recorder._get_army(action)
        
        self.assertEqual(army, mock_army)
        mock_game.get_my_army_by_number.assert_called_once_with(5)
    
    def test_get_army_no_identifier(self):
        """Test getting army without ID or number."""
        self.recorder.game = MagicMock()
        
        action = {}
        army = self.recorder._get_army(action)
        
        self.assertIsNone(army)


class TestRecorderCLI(unittest.TestCase):
    """Test CLI entry point."""
    
    def test_load_config_file(self):
        """Test loading configuration from file."""
        from conflict_interface.cli.recorder.__main__ import load_config_file
        
        # Create temporary config file
        config_data = {
            'username': 'test',
            'password': 'pass',
            'scenario_id': 5975
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            loaded_config = load_config_file(config_path)
            self.assertEqual(loaded_config['username'], 'test')
            self.assertEqual(loaded_config['scenario_id'], 5975)
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    unittest.main()
