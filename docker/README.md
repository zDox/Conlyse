# Docker Configuration Directory

This directory contains configuration files for the Docker deployment of ConflictInterface services.

## Directory Structure

```
docker/
├── server-observer-config/
│   ├── config.json         # Server Observer configuration
│   └── account_pool.json   # Game accounts for observation
└── server-converter-config/
    └── config.json         # Server Converter configuration
```

## Server Observer Configuration

### config.json

Key settings:
- `max_parallel_recordings` - Maximum number of concurrent game recordings
- `update_interval` - Seconds between game state updates
- `output_dir` - Directory for recordings (mapped to Docker volume)
- `redis` - Redis connection settings

### account_pool.json

Define game accounts for the Server Observer to use:

```json
{
  "accounts": [
    {
      "username": "your_account_name",
      "type": "guest",
      "enabled": true
    }
  ]
}
```

Account types:
- `guest` - Guest accounts (no authentication)
- `authenticated` - Accounts with credentials (add `password` field)

## Server Converter Configuration

### config.json

Key settings:

**Redis Configuration:**
- `host`, `port` - Redis connection (use service name `redis`)
- `stream_name` - Name of the Redis stream to consume
- `consumer_group` - Redis consumer group name
- `batch_size` - Number of messages to process per batch

**Storage Configuration:**
- `hot_storage_dir` - Local storage for active recordings
- `cold_storage_enabled` - Enable S3 archival
- `s3` - MinIO/S3 connection settings

**Database Configuration:**
- `host`, `port`, `database`, `user`, `password` - PostgreSQL connection

## Customization

### Changing Redis Stream Name

If you change the stream name, update both configs:

**server-observer-config/config.json:**
```json
"redis": {
  "stream_name": "your_custom_stream"
}
```

**server-converter-config/config.json:**
```json
"redis": {
  "stream_name": "your_custom_stream"
}
```

### Disabling S3 Storage

To disable S3 archival:

**server-converter-config/config.json:**
```json
"storage": {
  "cold_storage_enabled": false
}
```

### Using External S3 (AWS, Hetzner, etc.)

Replace MinIO settings with your S3 provider:

```json
"s3": {
  "endpoint_url": "https://s3.amazonaws.com",  // or your provider
  "access_key": "YOUR_ACCESS_KEY",
  "secret_key": "YOUR_SECRET_KEY",
  "bucket_name": "your-bucket",
  "region": "us-east-1"
}
```

## Environment Variables

Some settings can be overridden with environment variables (defined in `.env`):

- `POSTGRES_*` - Database credentials
- `MINIO_*` - MinIO credentials and bucket name

The configuration files will use these values when referenced.

## Validation

To validate your JSON configuration:

```bash
# Check if JSON is valid
cat docker/server-observer-config/config.json | python -m json.tool
cat docker/server-converter-config/config.json | python -m json.tool
```

## Notes

- Configuration files are mounted as read-only in containers
- Changes require service restart to take effect
- Use `./stack.sh restart-observer` or `./stack.sh restart-converter`
- Configuration paths inside containers differ from host paths
