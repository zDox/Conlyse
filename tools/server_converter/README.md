# Server Converter

Processes game responses from Redis streams and converts them to replay files.

## Overview

The Server Converter is a daemon that:
1. Consumes game responses from a Redis stream
2. Groups responses by game_id and player_id
3. Creates new replay files or appends to existing ones in hot storage
4. Optionally moves completed replays to cold storage (S3-compatible)
5. Tracks replay metadata in a SQLite database

## Configuration

Create a configuration file based on `config.example.json`:

```bash
cp config.example.json config.json
# Edit config.json with your settings
```

### Configuration Options

- **redis**: Redis connection settings
  - `host`: Redis server hostname
  - `port`: Redis server port
  - `db`: Redis database number
  - `password`: Redis password (optional)
  - `stream_name`: Name of the Redis stream to consume from
  - `consumer_group`: Consumer group name
  - `consumer_name`: This consumer's name
  - `batch_size`: Messages to read per batch

- **storage**: Storage configuration
  - `hot_storage_dir`: Local directory for active replays
  - `cold_storage_enabled`: Enable S3 cold storage
  - `s3`: S3 configuration (required if cold_storage_enabled is true)
    - `endpoint_url`: S3-compatible endpoint (e.g., Hetzner)
    - `access_key`: S3 access key
    - `secret_key`: S3 secret key
    - `bucket_name`: S3 bucket name
    - `region`: AWS region

- **database**: Database configuration
  - `db_path`: Path to SQLite database file

- **batch_size**: Number of messages to process per batch (default: 10)
- **check_interval_seconds**: Seconds to wait between checks (default: 5)

## Usage

```bash
# Run the server converter
server-converter config.json

# Run with verbose logging
server-converter config.json -v

# Run for limited iterations (testing)
server-converter config.json --max-iterations 10
```

## Redis Stream Format

The server converter expects messages in the Redis stream with the following fields:

- `timestamp`: Unix timestamp in milliseconds
- `game_id`: Game ID (integer)
- `player_id`: Player ID (integer)
- `response`: JSON response object (serialized as string)

Example message:
```python
{
    'timestamp': 1707825625000,
    'game_id': 12345,
    'player_id': 67890,
    'response': '{"result": {...}, "id": 1}'
}
```

## Database Schema

The converter maintains a SQLite database with the following schema:

```sql
CREATE TABLE replays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    replay_name TEXT NOT NULL UNIQUE,
    hot_storage_path TEXT,
    cold_storage_path TEXT,
    status TEXT NOT NULL,  -- 'recording', 'completed', 'archived'
    recording_start_time TEXT,
    recording_end_time TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    response_count INTEGER DEFAULT 0,
    UNIQUE(game_id, player_id)
);
```

## Workflow

1. **New Replay**: When responses arrive for a new game/player:
   - Creates a new replay file in hot storage
   - Creates a database entry with status 'recording'
   - Records the start time

2. **Appending**: For existing replays:
   - Appends new responses to the replay file
   - Increments the response count in the database

3. **Completion**: When a replay is marked as completed:
   - Updates the end time in the database
   - If cold storage is enabled:
     - Uploads the replay to S3
     - Deletes from hot storage
     - Updates status to 'archived'
   - Otherwise, updates status to 'completed'

## Integration with Server Observer

The Server Observer should publish responses to Redis using:

```python
redis_client.xadd(
    stream_name,
    {
        'timestamp': timestamp_ms,
        'game_id': game_id,
        'player_id': player_id,
        'response': json.dumps(response_data)
    }
)
```

## Dependencies

Required Python packages:
- `redis`: For Redis stream consumption
- `boto3`: For S3 cold storage (optional)

Install with:
```bash
pip install redis boto3
```

## Monitoring

The converter logs:
- Number of messages processed per batch
- Replay creation and append operations
- Cold storage uploads
- Database updates
- Errors and warnings

Enable verbose logging with `-v` flag for detailed debug information.
