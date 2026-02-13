"""
Tests for the server converter configuration module.
"""
import unittest
import tempfile
import json
from pathlib import Path

from tools.server_converter.config import (
    ServerConverterConfig,
    RedisConfig,
    S3Config,
    StorageConfig,
    DatabaseConfig
)


class TestServerConverterConfig(unittest.TestCase):
    """Test the ServerConverterConfig class."""
    
    def setUp(self):
        """Create a temporary config file for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        
    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_load_minimal_config(self):
        """Test loading a minimal configuration."""
        config_data = {
            "redis": {
                "host": "localhost",
                "port": 6379
            },
            "storage": {
                "hot_storage_dir": "/tmp/hot"
            },
            "database": {
                "db_path": "/tmp/replays.db"
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f)
            
        config = ServerConverterConfig.from_file(self.config_path)
        
        # Check Redis config
        self.assertEqual(config.redis.host, "localhost")
        self.assertEqual(config.redis.port, 6379)
        self.assertEqual(config.redis.stream_name, "game_responses")  # default
        
        # Check storage config
        self.assertEqual(config.storage.hot_storage_dir, Path("/tmp/hot"))
        self.assertFalse(config.storage.cold_storage_enabled)
        self.assertIsNone(config.storage.s3_config)
        
        # Check database config
        self.assertEqual(config.database.db_path, Path("/tmp/replays.db"))
        
    def test_load_full_config_with_s3(self):
        """Test loading a full configuration with S3."""
        config_data = {
            "redis": {
                "host": "redis.example.com",
                "port": 6380,
                "db": 1,
                "password": "secret",
                "stream_name": "custom_stream",
                "consumer_group": "custom_group",
                "consumer_name": "custom_consumer",
                "batch_size": 20
            },
            "storage": {
                "hot_storage_dir": "/data/hot",
                "cold_storage_enabled": True,
                "s3": {
                    "endpoint_url": "https://s3.example.com",
                    "access_key": "access123",
                    "secret_key": "secret123",
                    "bucket_name": "my-bucket",
                    "region": "eu-west-1"
                }
            },
            "database": {
                "db_path": "/data/replays.db"
            },
            "batch_size": 20,
            "check_interval_seconds": 10
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f)
            
        config = ServerConverterConfig.from_file(self.config_path)
        
        # Check Redis config
        self.assertEqual(config.redis.host, "redis.example.com")
        self.assertEqual(config.redis.port, 6380)
        self.assertEqual(config.redis.db, 1)
        self.assertEqual(config.redis.password, "secret")
        self.assertEqual(config.redis.stream_name, "custom_stream")
        self.assertEqual(config.redis.consumer_group, "custom_group")
        self.assertEqual(config.redis.consumer_name, "custom_consumer")
        self.assertEqual(config.redis.batch_size, 20)
        
        # Check storage config
        self.assertTrue(config.storage.cold_storage_enabled)
        self.assertIsNotNone(config.storage.s3_config)
        self.assertEqual(config.storage.s3_config.endpoint_url, "https://s3.example.com")
        self.assertEqual(config.storage.s3_config.access_key, "access123")
        self.assertEqual(config.storage.s3_config.secret_key, "secret123")
        self.assertEqual(config.storage.s3_config.bucket_name, "my-bucket")
        self.assertEqual(config.storage.s3_config.region, "eu-west-1")
        
        # Check other settings
        self.assertEqual(config.batch_size, 20)
        self.assertEqual(config.check_interval_seconds, 10)


if __name__ == '__main__':
    unittest.main()
