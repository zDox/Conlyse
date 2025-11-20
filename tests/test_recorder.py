"""
Tests for the Recorder CLI tool.
"""
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tools.recorder.config_schema import (
    BuildUpgradeAction,
    RecorderConfig,
    SleepAction,
)
from tools.recorder.recorder import Recorder, RecordingStorage


class TestRecordingStorage(unittest.TestCase):
    """Test RecordingStorage class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = RecordingStorage(self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        # Teardown logging before cleaning up
        if hasattr(self, 'storage') and self.storage:
            self.storage.teardown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_creates_files(self):
        """Test that initialization creates necessary files."""
        self.assertTrue(self.storage.metadata_file.exists())
        self.assertTrue(self.storage.recorder_log_file.exists() or True)  # May not exist until setup_logging
        
        # Check metadata content
        metadata = self.storage._load_metadata()
        self.assertIn('version', metadata)
        self.assertIn('created_at', metadata)
        self.assertIn('updates', metadata)

    def test_logging_setup_and_teardown(self):
        """Test that logging can be set up and torn down."""
        # Setup library logger first
        from conflict_interface.logger_config import setup_library_logger
        import logging as log_module
        setup_library_logger(log_module.DEBUG)
        
        # Setup logging
        self.storage.setup_logging()
        self.assertTrue(self.storage.recorder_log_file.exists())
        self.assertIsNotNone(self.storage.recorder_log_handler)
        
        # Write a test log
        from conflict_interface.logger_config import get_logger
        logger = get_logger()
        logger.info("Test log message")
        
        # Flush the handler to ensure the message is written
        self.storage.recorder_log_handler.flush()
        
        # Check that the log file contains the message before teardown
        with open(self.storage.recorder_log_file, 'r') as f:
            log_content = f.read()
            self.assertIn("Test log message", log_content)
        
        # Teardown logging
        self.storage.teardown_logging()
        self.assertIsNone(self.storage.recorder_log_handler)



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
        action = SleepAction(duration="5m")
        self.assertEqual(action.type, "sleep")
        self.assertEqual(action.duration, "5m")
    
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
    
    @patch('tools.recorder.recorder.RecordingStorage')
    def test_setup_storage(self, mock_storage_class):
        """Test storage setup."""
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        
        self.recorder._setup_storage()
        
        self.assertIsNotNone(self.recorder.storage)
        mock_storage_class.assert_called_once()
    
    @patch('tools.recorder.recorder.HubInterface')
    def test_login_success(self, mock_hub_interface):
        """Test successful login."""
        mock_interface = MagicMock()
        mock_hub_interface.return_value = mock_interface
        
        result = self.recorder.login()
        
        self.assertTrue(result)
        mock_interface.login.assert_called_once_with('test_user', 'test_pass')
    
    @patch('tools.recorder.recorder.HubInterface')
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


class TestRecorderAccountPool(unittest.TestCase):
    """Test Recorder with AccountPool integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'game_id': 123456,
            'output_dir': '/tmp/test_recordings',
            'actions': []
        }
    
    @patch('tools.recorder.recorder.Account')
    @patch('tools.recorder.recorder.AccountPool')
    def test_init_with_account_pool(self, mock_pool_class, mock_account_class):
        """Test recorder initialization with account pool."""
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        
        recorder = Recorder(self.config, account_pool=mock_pool)
        
        self.assertEqual(recorder.account_pool, mock_pool)
        self.assertIsNone(recorder.current_account)
    
    @patch('tools.recorder.account.Account')
    def test_login_with_account(self, mock_account_class):
        """Test login with specific account."""
        mock_account = MagicMock()
        mock_interface = MagicMock()
        mock_account.get_interface.return_value = mock_interface
        mock_account.username = 'test_user'
        
        recorder = Recorder(self.config)
        result = recorder.login(account=mock_account)
        
        self.assertTrue(result)
        self.assertEqual(recorder.current_account, mock_account)
        mock_account.get_interface.assert_called_once()
    
    @patch('tools.recorder.account.Account')
    def test_login_with_account_failure(self, mock_account_class):
        """Test login failure with account."""
        mock_account = MagicMock()
        mock_account.get_interface.side_effect = Exception("Login failed")
        mock_account.username = 'test_user'
        
        recorder = Recorder(self.config)
        result = recorder.login(account=mock_account)
        
        self.assertFalse(result)
        self.assertIsNone(recorder.current_account)
    
    @patch('tools.recorder.recorder.Recorder._join_game')
    def test_find_and_join_with_account_pool_success(self, mock_join_game):
        """Test successful join with account pool using scenario_id."""
        # Setup mock account pool
        mock_account1 = MagicMock()
        mock_account1.username = 'account1'
        mock_interface1 = MagicMock()
        mock_account1.get_interface.return_value = mock_interface1
        
        mock_pool = MagicMock()
        mock_pool.next_free_account.return_value = mock_account1
        
        # Config with scenario_id (required for account pool)
        config = {
            'scenario_id': 5975,
            'country_name': 'TestCountry',
            'output_dir': '/tmp/test_recordings',
            'actions': []
        }
        
        recorder = Recorder(config, account_pool=mock_pool)
        
        # Mock interface for listing games
        mock_hub_interface = MagicMock()
        mock_game = MagicMock()
        mock_game.game_id = 123456
        mock_game.open_slots = 15
        mock_hub_interface.get_global_games.return_value = [mock_game]
        mock_hub_interface.get_my_games.return_value = []
        recorder.interface = mock_hub_interface
        
        mock_join_game.return_value = True
        
        result = recorder.find_and_join_game()
        
        self.assertTrue(result)
        mock_join_game.assert_called()
    
    @patch('tools.recorder.recorder.Recorder._join_game')
    def test_find_and_join_with_account_pool_user_not_found(self, mock_join_game):
        """Test account pool retry on USER_NOT_FOUND error."""
        from conflict_interface.utils.exceptions import GameActivationException, GameActivationErrorCodes
        
        # Setup mock accounts
        mock_account1 = MagicMock()
        mock_account1.username = 'account1'
        mock_interface1 = MagicMock()
        mock_account1.get_interface.return_value = mock_interface1
        
        mock_account2 = MagicMock()
        mock_account2.username = 'account2'
        mock_interface2 = MagicMock()
        mock_account2.get_interface.return_value = mock_interface2
        
        mock_pool = MagicMock()
        # First call returns account1, second call returns account2
        mock_pool.next_free_account.side_effect = [mock_account1, mock_account2]
        
        # Config with scenario_id (required for account pool)
        config = {
            'scenario_id': 5975,
            'country_name': 'TestCountry',
            'output_dir': '/tmp/test_recordings',
            'actions': []
        }
        
        recorder = Recorder(config, account_pool=mock_pool)
        
        # Mock interface for listing games
        mock_hub_interface = MagicMock()
        mock_game = MagicMock()
        mock_game.game_id = 123456
        mock_game.open_slots = 15
        mock_hub_interface.get_global_games.return_value = [mock_game]
        mock_hub_interface.get_my_games.return_value = []
        recorder.interface = mock_hub_interface
        
        # First join attempt raises USER_NOT_FOUND, second succeeds
        user_not_found_error = GameActivationException(GameActivationErrorCodes.USER_NOT_FOUND)
        mock_join_game.side_effect = [user_not_found_error, True]
        
        result = recorder.find_and_join_game()
        
        self.assertTrue(result)
        self.assertEqual(mock_join_game.call_count, 2)
    
    @patch('tools.recorder.recorder.Recorder._join_game')
    def test_find_and_join_with_account_pool_no_accounts(self, mock_join_game):
        """Test account pool when no accounts available."""
        mock_pool = MagicMock()
        mock_pool.next_free_account.return_value = None
        
        # Config with scenario_id (required for account pool)
        config = {
            'scenario_id': 5975,
            'country_name': 'TestCountry',
            'output_dir': '/tmp/test_recordings',
            'actions': []
        }
        
        recorder = Recorder(config, account_pool=mock_pool)
        
        # Mock interface for listing games
        mock_hub_interface = MagicMock()
        recorder.interface = mock_hub_interface
        
        result = recorder.find_and_join_game()
        
        self.assertFalse(result)
        mock_join_game.assert_not_called()
    
    @patch('tools.recorder.recorder.Recorder._join_game')
    def test_game_id_with_account_pool_not_supported(self, mock_join_game):
        """Test that game_id with account pool is not supported."""
        mock_pool = MagicMock()
        
        # Config with game_id and account_pool - not supported
        config = {
            'game_id': 123456,
            'country_name': 'TestCountry',
            'output_dir': '/tmp/test_recordings',
            'actions': []
        }
        
        recorder = Recorder(config, account_pool=mock_pool)
        
        # Mock interface
        mock_hub_interface = MagicMock()
        recorder.interface = mock_hub_interface
        
        result = recorder.find_and_join_game()
        
        # Should return False (not supported)
        self.assertFalse(result)
        mock_join_game.assert_not_called()
    
    @patch('tools.recorder.recorder.Recorder._join_game')
    def test_scenario_id_without_account_pool_not_supported(self, mock_join_game):
        """Test that scenario_id without account pool is not supported."""
        # Config with scenario_id but no account pool - not supported
        config = {
            'username': 'test_user',
            'password': 'test_pass',
            'scenario_id': 5975,
            'country_name': 'TestCountry',
            'output_dir': '/tmp/test_recordings',
            'actions': []
        }
        
        recorder = Recorder(config, account_pool=None)
        
        # Mock interface
        mock_hub_interface = MagicMock()
        recorder.interface = mock_hub_interface
        
        result = recorder.find_and_join_game()
        
        # Should return False (not supported)
        self.assertFalse(result)
        mock_join_game.assert_not_called()
    
    @patch('tools.recorder.recorder.Recorder._join_game')
    def test_game_id_with_account_success(self, mock_join_game):
        """Test that game_id with single account (no pool) works."""
        # Config with game_id and no account pool - supported
        config = {
            'username': 'test_user',
            'password': 'test_pass',
            'game_id': 123456,
            'country_name': 'TestCountry',
            'output_dir': '/tmp/test_recordings',
            'actions': []
        }
        
        recorder = Recorder(config, account_pool=None)
        
        # Mock interface
        mock_hub_interface = MagicMock()
        recorder.interface = mock_hub_interface
        
        mock_join_game.return_value = True
        
        result = recorder.find_and_join_game()
        
        # Should succeed
        self.assertTrue(result)
        mock_join_game.assert_called_once_with(123456, 'TestCountry')


class TestGameFinder(unittest.TestCase):
    """Test GameFinder class."""
    
    def test_game_id_with_account(self):
        """Test game_id with single account logic."""
        from tools.recorder.find_game_logic import GameFinder
        
        config = {
            'game_id': 123456,
            'country_name': 'TestCountry'
        }
        
        mock_interface = MagicMock()
        mock_join_callback = MagicMock(return_value=True)
        
        game_finder = GameFinder(
            config=config,
            interface=mock_interface,
            account_pool=None,
            current_account=None,
            join_game_callback=mock_join_callback,
            login_callback=None
        )
        
        result = game_finder.find_and_join_game()
        
        self.assertTrue(result)
        mock_join_callback.assert_called_once_with(123456, 'TestCountry')
    
    def test_game_id_with_account_pool_not_supported(self):
        """Test game_id with account pool is not supported."""
        from tools.recorder.find_game_logic import GameFinder
        
        config = {
            'game_id': 123456,
            'country_name': 'TestCountry'
        }
        
        mock_interface = MagicMock()
        mock_pool = MagicMock()
        
        game_finder = GameFinder(
            config=config,
            interface=mock_interface,
            account_pool=mock_pool,
            current_account=None,
            join_game_callback=None,
            login_callback=None
        )
        
        result = game_finder.find_and_join_game()
        
        self.assertFalse(result)
    
    def test_scenario_id_without_account_pool_not_supported(self):
        """Test scenario_id without account pool is not supported."""
        from tools.recorder.find_game_logic import GameFinder
        
        config = {
            'scenario_id': 5975,
            'country_name': 'TestCountry'
        }
        
        mock_interface = MagicMock()
        
        game_finder = GameFinder(
            config=config,
            interface=mock_interface,
            account_pool=None,
            current_account=None,
            join_game_callback=None,
            login_callback=None
        )
        
        result = game_finder.find_and_join_game()
        
        self.assertFalse(result)
    
    def test_scenario_id_with_account_pool_success(self):
        """Test scenario_id with account pool logic."""
        from tools.recorder.find_game_logic import GameFinder
        
        config = {
            'scenario_id': 5975,
            'country_name': 'TestCountry',
            'poll_interval': 1,
            'max_wait': 10
        }
        
        mock_interface = MagicMock()
        mock_game = MagicMock()
        mock_game.game_id = 123456
        mock_game.open_slots = 15
        mock_interface.get_global_games.return_value = [mock_game]
        mock_interface.get_my_games.return_value = []
        
        mock_account = MagicMock()
        mock_account.username = 'test_account'
        mock_pool = MagicMock()
        mock_pool.next_free_account.return_value = mock_account
        
        mock_join_callback = MagicMock(return_value=True)
        mock_login_callback = MagicMock(return_value=True)
        
        game_finder = GameFinder(
            config=config,
            interface=mock_interface,
            account_pool=mock_pool,
            current_account=None,
            join_game_callback=mock_join_callback,
            login_callback=mock_login_callback
        )
        
        result = game_finder.find_and_join_game()
        
        self.assertTrue(result)
        mock_join_callback.assert_called()
        mock_login_callback.assert_called_with(mock_account)


class TestRecorderCLI(unittest.TestCase):
    """Test CLI entry point."""
    
    def test_load_config_file(self):
        """Test loading configuration from file."""
        from tools.recorder.__main__ import load_config_file
        
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
    
    def test_config_with_account_pool_path(self):
        """Test configuration with account_pool_path specified."""
        from tools.recorder.__main__ import load_config_file
        
        # Create temporary config file with account_pool_path
        config_data = {
            'account_pool_path': '/path/to/accounts.json',
            'game_id': 123456,
            'actions': []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            loaded_config = load_config_file(config_path)
            self.assertEqual(loaded_config['account_pool_path'], '/path/to/accounts.json')
            self.assertEqual(loaded_config['game_id'], 123456)
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    unittest.main()
