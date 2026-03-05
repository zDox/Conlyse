# Server Converter

Processes game responses from Redis streams and converts them to replay files.

## Overview

The Server Converter is a daemon that:
1. Consumes game responses from a Redis stream
2. Caches responses on disk until a game accumulates enough for processing
3. Creates new replay files or appends to existing ones in hot storage
4. Optionally moves completed replays to cold storage (S3-compatible)
5. Tracks replay metadata in a PostgreSQL database

## How It Works

The converter uses a **disk-based caching strategy** to efficiently handle mixed game streams:

1. **Caching Phase**: 
   - Reads messages from Redis stream
   - Immediately caches each response to disk (in `.response_cache/` subdirectory)
   - Acknowledges messages to Redis after successful caching

2. **Processing Phase**:
   - Checks which games have accumulated `batch_size` or more responses
   - Processes games that meet the threshold into replay files
   - Clears cache for successfully processed games

This approach:
- **Reduces memory usage** - responses stored on disk, not in memory
- **Handles restarts gracefully** - cached responses persist across restarts
- **Per-game batching** - each game accumulates independently until ready
- **Better for mixed streams** - efficiently handles many concurrent games

## Quick Start with Docker

The easiest way to run the server converter is using Docker Compose:

```bash
cd services/server_converter

# Create configuration file (use config.docker.json for Docker deployment)
cp config.docker.json config.json
# Edit config.json with your settings (database password, S3 credentials, etc.)

# Start all services (PostgreSQL, Redis, Server Converter)
docker-compose up -d

# View logs
docker-compose logs -f server-converter

# Stop all services
docker-compose down
```

**Note:** Use `config.docker.json` as the template for Docker deployments, as it has the correct paths (`/data/hot_storage`) that match the docker-compose volume mounts. For local development, use `config.example.json` which uses localhost connections.

## Configuration

Create a configuration file based on the appropriate template:

```bash
# For Docker deployment:
cp config.docker.json config.json

# For local development:
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
  - `batch_size`: **Minimum responses per game before processing** (default: 10)

- **storage**: Storage configuration
  - `hot_storage_dir`: Local directory for active replays (also stores `.response_cache/` subdirectory)
  - `cold_storage_enabled`: Enable S3 cold storage
  - `s3`: S3 configuration (required if cold_storage_enabled is true)
    - `endpoint_url`: S3-compatible endpoint (e.g., Hetzner)
    - `access_key`: S3 access key
    - `secret_key`: S3 secret key
    - `bucket_name`: S3 bucket name
    - `region`: AWS region

- **database**: PostgreSQL database configuration
  - `host`: PostgreSQL server hostname
  - `port`: PostgreSQL server port (default: 5432)
  - `database`: Database name
  - `user`: Database user
  - `password`: Database password

- **batch_size**: Number of messages to process per batch (default: 10)
- **check_interval_seconds**: Seconds to wait between checks (default: 5)
- **metrics_port**: Port for Prometheus metrics endpoint (default: 8000)

## Usage

```bash
# Run the server converter
server-converter config.json

# Run with verbose logging
server-converter config.json -v
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

The converter maintains a PostgreSQL database with the following schema:

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

### Querying the Database

```bash
psql -U converter -d replays -c "SELECT * FROM replays WHERE status='recording';"
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

### Prometheus Metrics

The server converter exposes Prometheus metrics on the configured metrics port (default: 8000). These metrics can be used to monitor performance, error rates, and resource utilization.

#### Available Metrics

**Message Processing Metrics:**
- `server_converter_messages_processed_total{status}` (Counter): Total messages processed, labeled by status (success/error)
- `server_converter_messages_processing_duration_seconds` (Histogram): Time spent processing message batches
- `server_converter_batch_size` (Summary): Distribution of batch sizes processed

**Replay Operation Metrics:**
- `server_converter_replay_operations_total{operation,status}` (Counter): Total replay operations, labeled by operation type (create/append/complete) and status (success/error)
- `server_converter_replay_creation_duration_seconds` (Histogram): Time spent creating new replays
- `server_converter_replay_append_duration_seconds` (Histogram): Time spent appending to existing replays
- `server_converter_responses_per_replay` (Summary): Distribution of responses added per replay operation

**Storage Metrics:**
- `server_converter_hot_storage_replays` (Gauge): Number of replays currently in hot storage
- `server_converter_cold_storage_uploads_total{status}` (Counter): Total uploads to cold storage, labeled by status (success/error)

**Database Metrics:**
- `server_converter_database_operations_total{operation,status}` (Counter): Total database operations, labeled by operation type and status
- `server_converter_database_operation_duration_seconds{operation}` (Histogram): Time spent on database operations

**Error Metrics:**
- `server_converter_errors_total{error_type}` (Counter): Total errors, labeled by error type (processing/database/storage/redis)

**Redis Metrics:**
- `server_converter_redis_consumer_lag` (Gauge): Number of pending messages in the consumer group
- `server_converter_redis_read_operations_total{status}` (Counter): Total Redis read operations

#### Accessing Metrics

```bash
# View metrics
curl http://localhost:8000/metrics

# Scrape with Prometheus
# Add to prometheus.yml:
scrape_configs:
  - job_name: 'server-converter'
    static_configs:
      - targets: ['localhost:8000']
```

#### Example Grafana Dashboards

**Message Throughput:**
```promql
rate(server_converter_messages_processed_total{status="success"}[5m])
```

**Error Rate:**
```promql
rate(server_converter_messages_processed_total{status="error"}[5m]) / 
rate(server_converter_messages_processed_total[5m])
```

**Average Processing Time:**
```promql
rate(server_converter_messages_processing_duration_seconds_sum[5m]) / 
rate(server_converter_messages_processing_duration_seconds_count[5m])
```

**Hot Storage Usage:**
```promql
server_converter_hot_storage_replays
```

### Logging

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
cd services/server_converter

# Create and edit configuration (use config.docker.json for Docker)
cp config.docker.json config.json
# Edit config.json - paths and service names are already configured correctly

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
docker build -f services/server_converter/Dockerfile -t server-converter:latest .

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

### Configuration inside Docker

The Docker image reads its settings from the `config.json` file mounted into the container (see the example above).
At present, configuration is not overridden via environment variables; values such as Redis and PostgreSQL
hosts, ports, credentials, and storage paths must be provided in `config.json`.

When running with Docker, ensure you:

- Mount your configuration file into the container, for example:

  ```bash
  docker run -d \
    -v $(pwd)/config.json:/app/config.json:ro \
    -v $(pwd)/hot_storage:/data/hot_storage \
    --network host \
    ghcr.io/zdox/server-converter:latest
