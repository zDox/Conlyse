# Server Converter

Processes game responses from Redis streams and converts them to replay files.

## Overview

The Server Converter is a daemon that:
1. Consumes game responses from a Redis stream
2. Groups responses by game_id and player_id
3. Creates new replay files or appends to existing ones in hot storage
4. Optionally moves completed replays to cold storage (S3-compatible)
5. Tracks replay metadata in a PostgreSQL or SQLite database

## Quick Start with Docker

The easiest way to run the server converter is using Docker Compose:

```bash
cd tools/server_converter

# Create configuration file
cp config.example.json config.json
# Edit config.json with your settings

# Start all services (PostgreSQL, Redis, Server Converter)
docker-compose up -d

# View logs
docker-compose logs -f server-converter

# Stop all services
docker-compose down
```

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
  - `type`: Database type - `"sqlite"` or `"postgres"`
  - For SQLite:
    - `db_path`: Path to SQLite database file
  - For PostgreSQL:
    - `host`: PostgreSQL server hostname
    - `port`: PostgreSQL server port (default: 5432)
    - `database`: Database name
    - `user`: Database user
    - `password`: Database password

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

The converter maintains a database (PostgreSQL or SQLite) with the following schema:

### PostgreSQL Schema

```sql
CREATE TABLE replays (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    replay_name VARCHAR(255) NOT NULL UNIQUE,
    hot_storage_path TEXT,
    cold_storage_path TEXT,
    status VARCHAR(50) NOT NULL,  -- 'recording', 'completed', 'archived'
    recording_start_time TIMESTAMP,
    recording_end_time TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    response_count INTEGER DEFAULT 0,
    UNIQUE(game_id, player_id)
);
```

### SQLite Schema

```sql
CREATE TABLE replays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    replay_name TEXT NOT NULL UNIQUE,
    hot_storage_path TEXT,
    cold_storage_path TEXT,
    status TEXT NOT NULL,  -- 'recording', 'completed', 'archived'
    recording_start_time TIMESTAMP,
    recording_end_time TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    response_count INTEGER DEFAULT 0,
    UNIQUE(game_id, player_id)
);
```

### Querying the Database

PostgreSQL:
```bash
psql -U converter -d replays -c "SELECT * FROM replays WHERE status='recording';"
```

SQLite:
```bash
sqlite3 /app/replays.db "SELECT * FROM replays WHERE status='recording';"
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

## Docker Deployment

### Using Docker Compose (Recommended)

The included `docker-compose.yml` sets up a complete stack with PostgreSQL, Redis, and the server converter:

```bash
cd tools/server_converter

# Create and edit configuration
cp config.example.json config.json
# Edit config.json - use host names from docker-compose (postgres, redis)

# Optional: Set PostgreSQL password
echo "POSTGRES_PASSWORD=your-secure-password" > .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f server-converter

# Check status
docker-compose ps

# Stop services
docker-compose down
```

### Building the Docker Image

```bash
# From repository root
docker build -f tools/server_converter/Dockerfile -t server-converter:latest .

# Run manually
docker run -d \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/hot_storage:/data/hot_storage \
  --network host \
  server-converter:latest
```

### Using Pre-built Image from GitHub Container Registry

```bash
# Pull the latest image
docker pull ghcr.io/zdox/server-converter:latest

# Run with config
docker run -d \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/hot_storage:/data/hot_storage \
  --network host \
  ghcr.io/zdox/server-converter:latest
```

### Environment Variables

The Docker image supports configuration via environment variables:

- `REDIS_HOST`: Override Redis hostname (default from config)
- `REDIS_PORT`: Override Redis port
- `POSTGRES_HOST`: Override PostgreSQL hostname
- `POSTGRES_PORT`: Override PostgreSQL port
- `POSTGRES_DB`: Override database name
- `POSTGRES_USER`: Override database user
- `POSTGRES_PASSWORD`: Override database password

Example with environment variables:

```bash
docker run -d \
  -e REDIS_HOST=redis.example.com \
  -e POSTGRES_HOST=db.example.com \
  -e POSTGRES_PASSWORD=secret \
  -v $(pwd)/config.json:/app/config.json:ro \
  server-converter:latest
```
