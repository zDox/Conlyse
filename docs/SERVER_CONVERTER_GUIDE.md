# Server Converter System Integration Guide

This guide explains how to set up and use the complete server converter system for automated replay generation.

## Overview

The server converter system consists of two main components:

1. **Server Observer** (C++): Monitors games and publishes responses to a Redis stream
2. **Server Converter** (Python): Consumes responses from Redis and creates/manages replay files

## Architecture

```
┌─────────────────┐
│ Server Observer │ ──> Publishes responses
└─────────────────┘
         │
         ▼
   ┌──────────┐
   │  Redis   │ ──> Stream: game_responses
   │  Stream  │
   └──────────┘
         │
         ▼
┌─────────────────┐
│Server Converter │ ──> Manages replays
└─────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────┐   ┌─────┐
│ Hot │   │ DB  │
│Store│   │Meta │
└─────┘   └─────┘
    │
    ▼
┌─────┐
│ S3  │ (optional)
│Cold │
└─────┘
```

## Prerequisites

### Redis

Install Redis server:

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

### Python Dependencies

Install required Python packages:

```bash
# Install server-converter dependencies
pip install redis boto3

# Or install with extras
pip install -e ".[tools-server-converter]"
```

### C++ Dependencies (for Server Observer)

Install hiredis for Redis support:

```bash
# Ubuntu/Debian
sudo apt-get install libhiredis-dev

# macOS
brew install hiredis
```

Build server_observer with Redis support:

```bash
cd tools/server_observer
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DENABLE_REDIS=ON ..
make -j$(nproc)
```

## Configuration

### 1. Configure Server Observer

Create `tools/server_observer/config.json`:

```json
{
  "max_parallel_recordings": 5,
  "update_interval": 60,
  "output_dir": "/data/recordings",
  "output_metadata_dir": "/data/metadata",
  "long_term_storage_path": "",
  "file_size_threshold": 0,
  "redis": {
    "host": "localhost",
    "port": 6379,
    "stream_name": "game_responses"
  }
}
```

### 2. Configure Server Converter

Create `tools/server_converter/config.json`:

```json
{
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "stream_name": "game_responses",
    "consumer_group": "server_converter",
    "consumer_name": "converter_1",
    "batch_size": 10
  },
  "storage": {
    "hot_storage_dir": "/data/hot_storage",
    "cold_storage_enabled": true,
    "s3": {
      "endpoint_url": "https://your-s3-endpoint.com",
      "access_key": "YOUR_ACCESS_KEY",
      "secret_key": "YOUR_SECRET_KEY",
      "bucket_name": "replays",
      "region": "us-east-1"
    }
  },
  "database": {
    "db_path": "/data/replays.db"
  },
  "batch_size": 10,
  "check_interval_seconds": 5
}
```

### S3-Compatible Storage (Hetzner)

For Hetzner storage, use:

```json
{
  "s3": {
    "endpoint_url": "https://fsn1.your-objectstorage.com",
    "access_key": "YOUR_HETZNER_ACCESS_KEY",
    "secret_key": "YOUR_HETZNER_SECRET_KEY",
    "bucket_name": "replays",
    "region": "us-east-1"
  }
}
```

## Running the System

### 1. Start Redis

```bash
redis-server
```

### 2. Start Server Observer

```bash
cd tools/server_observer/build
./server_observer ../config.json
```

The server observer will:
- Monitor games for updates
- Publish responses to Redis stream `game_responses`
- Continue saving responses to local files as backup

### 3. Start Server Converter

```bash
server-converter tools/server_converter/config.json -v
```

The server converter will:
- Consume responses from Redis stream
- Create new replay files for new games
- Append responses to existing replays
- Move completed replays to S3 cold storage
- Track metadata in SQLite database

## Workflow

### New Game Detection

1. Server Observer detects a new game
2. Publishes initial game state to Redis
3. Server Converter receives responses (waits for ≥10)
4. Creates new replay file in hot storage
5. Creates database entry with status='recording'

### Ongoing Updates

1. Server Observer publishes game updates to Redis
2. Server Converter consumes updates in batches
3. Appends responses to existing replay file
4. Updates response count in database

### Game Completion

When a game ends:

1. Server Observer publishes final state
2. Server Converter processes final responses
3. Marks replay as completed in database
4. If S3 enabled:
   - Uploads replay to S3
   - Deletes from hot storage
   - Updates database with S3 path
   - Sets status='archived'

## Database Schema

The server converter maintains a SQLite database with replay metadata:

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

Query the database:

```bash
sqlite3 /data/replays.db "SELECT * FROM replays WHERE status='recording';"
```

## Monitoring

### Redis Stream

Monitor Redis stream:

```bash
# Check stream length
redis-cli XLEN game_responses

# View recent messages
redis-cli XRANGE game_responses - + COUNT 10

# Check consumer group status
redis-cli XINFO GROUPS game_responses
```

### Server Converter Logs

Enable verbose logging:

```bash
server-converter config.json -v
```

Key log messages:
- "Processing X messages"
- "Creating new replay for game X"
- "Appending Y responses to existing replay"
- "Uploaded replay to S3: ..."

### Database Status

Check replay status:

```bash
sqlite3 /data/replays.db << EOF
SELECT 
    status, 
    COUNT(*) as count,
    SUM(response_count) as total_responses
FROM replays 
GROUP BY status;
EOF
```

## Troubleshooting

### Redis Connection Issues

```bash
# Test Redis connection
redis-cli ping
# Should return: PONG

# Check if stream exists
redis-cli EXISTS game_responses
```

### S3 Upload Failures

Check S3 credentials and endpoint:

```python
import boto3
client = boto3.client(
    's3',
    endpoint_url='https://your-endpoint.com',
    aws_access_key_id='YOUR_KEY',
    aws_secret_access_key='YOUR_SECRET'
)
client.list_buckets()
```

### Missing Dependencies

If server observer doesn't publish to Redis:
- Ensure it was built with `-DENABLE_REDIS=ON`
- Check for Redis config in config.json

If server converter can't connect to Redis:
```bash
pip install redis
```

## Performance Tuning

### Batch Size

Adjust `batch_size` to process more/fewer messages per iteration:

```json
{
  "batch_size": 20,  // Process 20 responses at a time
  "redis": {
    "batch_size": 20  // Read 20 messages from Redis
  }
}
```

### Multiple Converters

Run multiple server converters for redundancy:

```json
{
  "redis": {
    "consumer_group": "server_converter",
    "consumer_name": "converter_1"  // Change to converter_2, converter_3, etc.
  }
}
```

Each converter will process different messages from the same stream.

### Hot Storage vs Cold Storage

- **Hot Storage**: Fast local SSD for active replays
- **Cold Storage**: S3 for archived replays

Configure thresholds:

```json
{
  "storage": {
    "hot_storage_dir": "/fast-ssd/hot",
    "cold_storage_enabled": true
  }
}
```

## Security Considerations

### Redis Security

Secure Redis with password:

```bash
# In redis.conf
requirepass YOUR_REDIS_PASSWORD
```

Update configs:

```json
{
  "redis": {
    "password": "YOUR_REDIS_PASSWORD"
  }
}
```

### S3 Credentials

- Never commit credentials to git
- Use environment variables or secrets manager
- Rotate access keys regularly

### Database Security

- Store database file in secure location
- Backup regularly
- Restrict file permissions:

```bash
chmod 600 /data/replays.db
```

## Deployment

### Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  server-converter:
    build: .
    volumes:
      - ./config.json:/app/config.json
      - ./hot_storage:/data/hot_storage
      - ./replays.db:/data/replays.db
    depends_on:
      - redis
    command: server-converter /app/config.json -v

volumes:
  redis-data:
```

### Systemd Service

Create `/etc/systemd/system/server-converter.service`:

```ini
[Unit]
Description=Server Converter
After=network.target redis.service

[Service]
Type=simple
User=converter
WorkingDirectory=/opt/server-converter
ExecStart=/usr/local/bin/server-converter /opt/server-converter/config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable server-converter
sudo systemctl start server-converter
```

## Backup and Recovery

### Database Backup

```bash
# Backup database
sqlite3 /data/replays.db ".backup /backup/replays_$(date +%Y%m%d).db"

# Restore from backup
sqlite3 /data/replays.db ".restore /backup/replays_20240115.db"
```

### Replay File Backup

Hot storage is automatically backed up to S3 when cold storage is enabled.

For additional backup:

```bash
# Sync hot storage to backup location
rsync -av /data/hot_storage/ /backup/hot_storage/
```

## Next Steps

- Monitor system performance with logs
- Set up alerts for failures
- Configure automatic cleanup of old replays
- Integrate with analysis tools

For more details, see:
- [Server Converter README](../tools/server_converter/README.md)
- [Server Observer README](../tools/server_observer/README.md)
- [Replay System Documentation](REPLAY_SYSTEM.md)

## PostgreSQL Setup

### Installing PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql@16
brew services start postgresql@16

# Docker (recommended for development)
docker run -d \
  --name replays-postgres \
  -e POSTGRES_DB=replays \
  -e POSTGRES_USER=converter \
  -e POSTGRES_PASSWORD=changeme \
  -p 5432:5432 \
  postgres:16-alpine
```

### Creating the Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create user and database
CREATE USER converter WITH PASSWORD 'changeme';
CREATE DATABASE replays OWNER converter;
GRANT ALL PRIVILEGES ON DATABASE replays TO converter;

# Exit
\q
```

### PostgreSQL Configuration

Update your server_converter config.json:

```json
{
  "database": {
    "type": "postgres",
    "host": "localhost",
    "port": 5432,
    "database": "replays",
    "user": "converter",
    "password": "changeme"
  }
}
```

### Database Migrations

The server_converter automatically creates tables on first run. For existing SQLite databases, you can migrate data:

```python
# Example migration script
import sqlite3
import psycopg2
from datetime import datetime

# Connect to both databases
sqlite_conn = sqlite3.connect('replays.db')
pg_conn = psycopg2.connect(
    host='localhost',
    database='replays',
    user='converter',
    password='changeme'
)

# Read from SQLite
sqlite_cur = sqlite_conn.cursor()
sqlite_cur.execute("SELECT * FROM replays")
rows = sqlite_cur.fetchall()

# Write to PostgreSQL
pg_cur = pg_conn.cursor()
for row in rows:
    pg_cur.execute("""
        INSERT INTO replays 
        (game_id, player_id, replay_name, hot_storage_path, cold_storage_path,
         status, recording_start_time, recording_end_time, created_at, 
         updated_at, response_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, row[1:])  # Skip the id column

pg_conn.commit()
print(f"Migrated {len(rows)} replays")
```

### PostgreSQL Performance Tuning

For production deployments, tune PostgreSQL settings in `postgresql.conf`:

```ini
# Memory settings (adjust based on your system)
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB

# Connection settings
max_connections = 100

# Write-ahead log
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Query planner
random_page_cost = 1.1  # For SSD storage
```

Restart PostgreSQL after changes:

```bash
sudo systemctl restart postgresql
```

### Monitoring PostgreSQL

Check database size:

```sql
SELECT pg_size_pretty(pg_database_size('replays'));
```

Check table statistics:

```sql
SELECT 
    schemaname,
    tablename,
    n_live_tup as "Rows",
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as "Size"
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

Active connections:

```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = 'replays';
```

Long-running queries:

```sql
SELECT 
    pid,
    now() - query_start as duration,
    query
FROM pg_stat_activity
WHERE state = 'active'
AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;
```
