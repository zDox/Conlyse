"""
Configuration management for the server converter.
"""
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    stream_name: str = "game_responses"
    consumer_group: str = "server_converter"
    consumer_name: str = "converter_1"
    batch_size: int = 10


@dataclass
class S3Config:
    """S3-compatible storage configuration."""
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket_name: str
    region: str = "us-east-1"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    db_path: Path


@dataclass
class StorageConfig:
    """Storage paths configuration."""
    hot_storage_dir: Path
    cold_storage_enabled: bool = False
    s3_config: Optional[S3Config] = None


@dataclass
class ServerConverterConfig:
    """Main configuration for server converter."""
    redis: RedisConfig
    storage: StorageConfig
    database: DatabaseConfig
    batch_size: int = 10
    check_interval_seconds: int = 5

    @classmethod
    def from_file(cls, config_path: Path) -> 'ServerConverterConfig':
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        # Parse Redis config
        redis_data = data.get('redis', {})
        redis_config = RedisConfig(
            host=redis_data.get('host', 'localhost'),
            port=redis_data.get('port', 6379),
            db=redis_data.get('db', 0),
            password=redis_data.get('password'),
            stream_name=redis_data.get('stream_name', 'game_responses'),
            consumer_group=redis_data.get('consumer_group', 'server_converter'),
            consumer_name=redis_data.get('consumer_name', 'converter_1'),
            batch_size=redis_data.get('batch_size', 10)
        )
        
        # Parse storage config
        storage_data = data.get('storage', {})
        s3_config = None
        if 's3' in storage_data:
            s3_data = storage_data['s3']
            s3_config = S3Config(
                endpoint_url=s3_data['endpoint_url'],
                access_key=s3_data['access_key'],
                secret_key=s3_data['secret_key'],
                bucket_name=s3_data['bucket_name'],
                region=s3_data.get('region', 'us-east-1')
            )
        
        storage_config = StorageConfig(
            hot_storage_dir=Path(storage_data['hot_storage_dir']),
            cold_storage_enabled=storage_data.get('cold_storage_enabled', False),
            s3_config=s3_config
        )
        
        # Parse database config
        db_data = data.get('database', {})
        database_config = DatabaseConfig(
            db_path=Path(db_data.get('db_path', 'replays.db'))
        )
        
        return cls(
            redis=redis_config,
            storage=storage_config,
            database=database_config,
            batch_size=data.get('batch_size', 10),
            check_interval_seconds=data.get('check_interval_seconds', 5)
        )
