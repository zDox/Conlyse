"""
Unit tests for server converter Prometheus metrics.

Tests verify that metrics are properly recorded during server converter operations.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from tools.server_converter.converter import ServerConverter
from tools.server_converter.config import (
    ServerConverterConfig, RedisConfig, StorageConfig, DatabaseConfig
)
from tools.server_converter import metrics


class ServerConverterMetricsTests(unittest.TestCase):
    """Test that Prometheus metrics are properly recorded."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for hot storage
        self.temp_dir = tempfile.mkdtemp()
        self.hot_storage_path = Path(self.temp_dir)
        
        # Create test configuration
        self.config = ServerConverterConfig(
            redis=RedisConfig(
                host='localhost',
                port=6379,
                batch_size=10
            ),
            storage=StorageConfig(
                hot_storage_dir=self.hot_storage_path,
                cold_storage_enabled=False
            ),
            database=DatabaseConfig(
                host='localhost',
                port=5432,
                database='test_replays',
                user='test_user',
                password='test_password'
            )
        )

    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch('tools.server_converter.converter.ReplayDatabase')
    @patch('tools.server_converter.converter.RedisStreamConsumer')
    def test_messages_processed_metric(self, mock_redis_consumer_class, mock_db_class):
        """Test that messages_processed_total metric is incremented."""
        # Setup mocks
        mock_redis = Mock()
        mock_redis_consumer_class.return_value = mock_redis
        
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_replay_by_game_and_player.return_value = None
        
        # Create sample messages
        messages = [
            ('msg1', {'game_id': 1, 'player_id': 1, 'timestamp': 1000, 'response': {'data': 'test'}}),
            ('msg2', {'game_id': 1, 'player_id': 1, 'timestamp': 2000, 'response': {'data': 'test2'}})
        ]
        mock_redis.read_messages.return_value = messages
        mock_redis.acknowledge_messages.return_value = None
        
        # Get initial metric value
        initial_success = metrics.messages_processed_total.labels(status='success')._value.get()
        
        # Create converter and process batch
        with patch('tools.server_converter.converter.ReplayBuilder'):
            mock_db.get_replay_by_game_and_player.side_effect = [None, {'id': 1}]
            converter = ServerConverter(self.config)
            converter.process_batch()
        
        # Verify metric was incremented
        final_success = metrics.messages_processed_total.labels(status='success')._value.get()
        self.assertGreater(final_success, initial_success)

    @patch('tools.server_converter.converter.ReplayDatabase')
    @patch('tools.server_converter.converter.RedisStreamConsumer')
    def test_processing_duration_metric(self, mock_redis_consumer_class, mock_db_class):
        """Test that messages_processing_duration_seconds histogram is observed."""
        # Setup mocks
        mock_redis = Mock()
        mock_redis_consumer_class.return_value = mock_redis
        mock_redis.read_messages.return_value = []
        
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        # Access histogram sample count before
        initial_count = metrics.messages_processing_duration_seconds.collect()[0].samples[0].value
        
        # Create converter and process batch
        converter = ServerConverter(self.config)
        converter.process_batch()
        
        # Verify histogram was observed
        final_count = metrics.messages_processing_duration_seconds.collect()[0].samples[0].value
        self.assertGreater(final_count, initial_count)

    @patch('tools.server_converter.converter.ReplayDatabase')
    @patch('tools.server_converter.converter.RedisStreamConsumer')
    @patch('tools.server_converter.converter.ReplayBuilder')
    def test_replay_creation_metrics(self, mock_builder_class, mock_redis_consumer_class, mock_db_class):
        """Test that replay creation metrics are recorded."""
        # Setup mocks
        mock_redis = Mock()
        mock_redis_consumer_class.return_value = mock_redis
        
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        # Setup side effect for get_replay_by_game_and_player
        # First call returns None (no existing replay), second call returns the created entry
        mock_db.get_replay_by_game_and_player.side_effect = [None, {'id': 1, 'response_count': 0}]
        mock_db.create_replay_entry.return_value = None
        
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder
        mock_builder.create_replay.return_value = 0
        
        messages = [
            ('msg1', {'game_id': 1, 'player_id': 1, 'timestamp': 1000, 'response': {'data': 'test'}})
        ]
        mock_redis.read_messages.return_value = messages
        mock_redis.acknowledge_messages.return_value = None
        
        # Get initial metrics
        initial_operations = metrics.replay_operations_total.labels(operation='create', status='success')._value.get()
        initial_hot_storage = metrics.hot_storage_replays._value.get()
        
        # Create converter and process batch
        converter = ServerConverter(self.config)
        converter.process_batch()
        
        # Verify metrics were updated
        final_operations = metrics.replay_operations_total.labels(operation='create', status='success')._value.get()
        final_hot_storage = metrics.hot_storage_replays._value.get()
        
        self.assertGreater(final_operations, initial_operations)
        self.assertGreater(final_hot_storage, initial_hot_storage)

    @patch('tools.server_converter.converter.ReplayDatabase')
    @patch('tools.server_converter.converter.RedisStreamConsumer')
    @patch('tools.server_converter.converter.ReplayBuilder')
    def test_replay_append_metrics(self, mock_builder_class, mock_redis_consumer_class, mock_db_class):
        """Test that replay append metrics are recorded."""
        # Setup mocks
        mock_redis = Mock()
        mock_redis_consumer_class.return_value = mock_redis
        
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        # Simulate existing replay
        replay_entry = {'id': 1, 'response_count': 5}
        mock_db.get_replay_by_game_and_player.return_value = replay_entry
        
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder
        mock_builder.append_json_responses.return_value = None
        
        # Create a fake replay file
        replay_path = self.hot_storage_path / "game_1_player_1.bin"
        replay_path.write_text("fake replay data")
        
        messages = [
            ('msg1', {'game_id': 1, 'player_id': 1, 'timestamp': 1000, 'response': {'data': 'test'}})
        ]
        mock_redis.read_messages.return_value = messages
        mock_redis.acknowledge_messages.return_value = None
        
        # Get initial metrics
        initial_operations = metrics.replay_operations_total.labels(operation='append', status='success')._value.get()
        
        # Create converter and process batch
        converter = ServerConverter(self.config)
        converter.process_batch()
        
        # Verify metrics were updated
        final_operations = metrics.replay_operations_total.labels(operation='append', status='success')._value.get()
        
        self.assertGreater(final_operations, initial_operations)

    @patch('tools.server_converter.converter.ReplayDatabase')
    @patch('tools.server_converter.converter.RedisStreamConsumer')
    def test_error_metrics(self, mock_redis_consumer_class, mock_db_class):
        """Test that error metrics are recorded when processing fails."""
        # Setup mocks to trigger an error
        mock_redis = Mock()
        mock_redis_consumer_class.return_value = mock_redis
        
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        # Make database raise an exception
        mock_db.get_replay_by_game_and_player.side_effect = Exception("Database error")
        
        messages = [
            ('msg1', {'game_id': 1, 'player_id': 1, 'timestamp': 1000, 'response': {'data': 'test'}})
        ]
        mock_redis.read_messages.return_value = messages
        mock_redis.acknowledge_messages.return_value = None
        
        # Get initial metrics
        initial_processing_errors = metrics.messages_processed_total.labels(status='error')._value.get()
        initial_errors = metrics.errors_total.labels(error_type='processing')._value.get()
        
        # Create converter and process batch
        converter = ServerConverter(self.config)
        converter.process_batch()
        
        # Verify error metrics were incremented
        final_processing_errors = metrics.messages_processed_total.labels(status='error')._value.get()
        final_errors = metrics.errors_total.labels(error_type='processing')._value.get()
        
        self.assertGreater(final_processing_errors, initial_processing_errors)
        self.assertGreater(final_errors, initial_errors)

    @patch('tools.server_converter.converter.ReplayDatabase')
    @patch('tools.server_converter.converter.RedisStreamConsumer')
    def test_batch_size_summary(self, mock_redis_consumer_class, mock_db_class):
        """Test that batch_size_summary is observed."""
        # Setup mocks
        mock_redis = Mock()
        mock_redis_consumer_class.return_value = mock_redis
        
        messages = [
            ('msg1', {'game_id': 1, 'player_id': 1, 'timestamp': 1000, 'response': {'data': 'test'}}),
            ('msg2', {'game_id': 1, 'player_id': 1, 'timestamp': 2000, 'response': {'data': 'test2'}}),
            ('msg3', {'game_id': 1, 'player_id': 1, 'timestamp': 3000, 'response': {'data': 'test3'}})
        ]
        mock_redis.read_messages.return_value = messages
        mock_redis.acknowledge_messages.return_value = None
        
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_replay_by_game_and_player.return_value = None
        
        # Get initial count from summary samples
        initial_count = metrics.batch_size_summary.collect()[0].samples[0].value
        
        # Create converter and process batch
        with patch('tools.server_converter.converter.ReplayBuilder'):
            mock_db.get_replay_by_game_and_player.side_effect = [None, {'id': 1}]
            converter = ServerConverter(self.config)
            converter.process_batch()
        
        # Verify summary was observed
        final_count = metrics.batch_size_summary.collect()[0].samples[0].value
        self.assertGreater(final_count, initial_count)

    @patch('tools.server_converter.converter.ReplayDatabase')
    @patch('tools.server_converter.converter.RedisStreamConsumer')
    def test_hot_storage_gauge_update(self, mock_redis_consumer_class, mock_db_class):
        """Test that hot storage gauge is updated."""
        # Setup mocks
        mock_redis = Mock()
        mock_redis_consumer_class.return_value = mock_redis
        mock_redis.read_messages.return_value = []
        
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        # Create some fake replay files
        (self.hot_storage_path / "game_1_player_1.bin").write_text("data1")
        (self.hot_storage_path / "game_2_player_2.bin").write_text("data2")
        (self.hot_storage_path / "game_3_player_3.bin").write_text("data3")
        
        # Create converter
        converter = ServerConverter(self.config)
        
        # Update hot storage metric manually
        converter._update_hot_storage_metric()
        
        # Verify gauge shows correct count
        gauge_value = metrics.hot_storage_replays._value.get()
        self.assertEqual(gauge_value, 3)


if __name__ == '__main__':
    unittest.main()
