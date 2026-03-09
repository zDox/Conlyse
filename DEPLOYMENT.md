# Conlyse Full Stack Deployment

This guide explains how to deploy the complete ConflictInterface stack using Docker Compose. The stack provides an automated system for recording and storing game replays.

## Overview

The deployment includes six main components:

- **PostgreSQL** - Database for replay metadata, user accounts, and API state
- **Redis** - Message stream for real-time game response data
- **MinIO** - S3-compatible object storage for replay files and Conlyse binaries
- **Server Observer** - Monitors live games and captures responses
- **Server Converter** - Processes responses and creates replay files
- **Conlyse API** - FastAPI service for authentication, downloads, and user management

## Deployment Steps

### 1. Prepare Environment Configuration

Create and configure your environment file:

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your preferred text editor
nano .env  # or vim, vi, etc.
```

**Required Environment Variables:**

```bash
# PostgreSQL Configuration
POSTGRES_USER=converter
POSTGRES_PASSWORD=<strong-password-here>
POSTGRES_DB=replays

# MinIO Configuration
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<strong-password-here>

# Redis Configuration (optional password)
REDIS_PASSWORD=<optional-password>

# Conlyse API
JWT_SECRET_KEY=<strong-random-secret-here>
```

### 2. Configure Services

#### Server Observer Configuration

Edit `infra/prod/server-observer-config.toml`:

```toml
max_parallel_recordings = 1
max_parallel_normal_recordings = 1
update_interval = 10
max_parallel_updates = 10
max_parallel_first_updates = 10
update_worker_threads = 4
output_dir = "/app/recordings"
output_metadata_dir = "/app/recordings/metadata"

[redis]
host = "redis"
port = 6379
stream_name = "game_responses"

[game_finder]
enabled = false
scan_interval_seconds = 300
max_games_per_scan = 10
```

Add game accounts to `infra/prod/account_pool.json`:

```json
[
  {
    "username": "account1",
    "password": "password1"
  },
  {
    "username": "account2",
    "password": "password2"
  }
]
```

#### Server Converter Configuration

Edit `infra/prod/server-converter-config.json`:

```json
{
  "redis": {
    "host": "redis",
    "port": 6379,
    "stream_name": "game_responses",
    "consumer_group": "converters"
  },
  "database": {
    "host": "postgres",
    "port": 5432,
    "database": "replays",
    "user": "converter"
  },
  "s3": {
    "endpoint": "http://minio:9000",
    "bucket": "replays",
    "access_key": "minioadmin",
    "secret_key": "minioadmin"
  }
}
```

### 3. Deploy the Stack

Start all services using Docker Compose:

```bash
# Start all services in detached mode
docker compose -f infra/docker-compose.yml up -d

# Check service status
docker compose -f infra/docker-compose.yml ps

# View logs for all services
docker compose -f infra/docker-compose.yml logs -f

# View logs for specific service
docker compose -f infra/docker-compose.yml logs -f server-observer
docker compose -f infra/docker-compose.yml logs -f server-converter
```

### 4. Verify Deployment

Check that all services are healthy:

```bash
docker compose -f infra/docker-compose.yml ps
```

All services should show `(healthy)` status within 1-2 minutes.

### 5. Initial Setup Verification

Verify the MinIO bucket was created:

```bash
docker compose -f infra/docker-compose.yml logs minio-init
```

You should see: "Bucket 'replays' created successfully"

Check PostgreSQL connectivity:

```bash
docker compose -f infra/docker-compose.yml exec postgres psql -U converter -d replays
# Inside PostgreSQL shell:
\dt  # List tables
\q   # Quit
```

Check Redis stream:

```bash
docker compose -f infra/docker-compose.yml exec redis redis-cli
# Inside Redis CLI:
INFO
QUIT
```

## Accessing Deployed Services

Once the stack is running, you can access the various services:

### Conlyse API

- **URL**: [http://localhost:8000](http://localhost:8000)
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health check**: [http://localhost:8000/health](http://localhost:8000/health)

**Running database migrations:**

```bash
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
```

**Creating the first admin user (example via API):**

```bash
# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","username":"admin","password":"changeme123"}'

# Promote to admin via DB (first time only)
docker compose -f infra/docker-compose.yml exec postgres psql -U converter -d replays \
  -c "UPDATE users SET role='admin' WHERE username='admin';"
```

### MinIO Console (S3 Storage)

- **URL**: [http://localhost:9001](http://localhost:9001)
- **Username**: Value from `MINIO_ROOT_USER` in `.env` (default: `minioadmin`)
- **Password**: Value from `MINIO_ROOT_PASSWORD` in `.env` (default: `minioadmin`)

**What you can do:**

- Browse uploaded replay files in the `replays` bucket
- Download replay files
- Monitor storage usage
- Manage bucket policies

### PostgreSQL Database

- **Host**: `localhost:5432`
- **Database**: `replays`
- **Username**: Value from `POSTGRES_USER` in `.env` (default: `converter`)
- **Password**: Value from `POSTGRES_PASSWORD` in `.env`

**Connect using psql:**

```bash
docker compose -f infra/docker-compose.yml exec postgres psql -U converter -d replays
```

**Connect using external tools:**

```bash
psql -h localhost -p 5432 -U converter -d replays
```

**Useful queries:**

```sql
-- View all replays
SELECT * FROM replays;

-- View active recordings
SELECT * FROM replays WHERE status = 'recording';

-- Count replays by status
SELECT status, COUNT(*) FROM replays GROUP BY status;
```

### Redis Stream

- **Host**: `localhost:6379`
- **Password**: Value from `REDIS_PASSWORD` in `.env` (if set)

**Connect using redis-cli:**

```bash
docker compose -f infra/docker-compose.yml exec redis redis-cli
```

**Useful commands:**

```bash
# View stream length
XLEN game_responses

# View recent entries
XRANGE game_responses - + COUNT 10

# View consumer group info
XINFO GROUPS game_responses
```

## Architecture

```
┌─────────────────┐
│ Server Observer │──> Monitors games
└────────┬────────┘
         │
         ▼
    ┌────────┐
    │ Redis  │──> Streams game responses
    └────┬───┘
         │
         ▼
┌─────────────────┐
│Server Converter │──> Processes streams
└────┬───────┬────┘
     │       │
     ▼       ▼
┌────────┐ ┌─────────┐
│Postgres│ │ MinIO   │──> Stores replays
│  DB    │ │  (S3)   │
└────────┘ └─────────┘
```

## Data Persistence

The following data is persisted in Docker volumes:

- `postgres-data` - Database data
- `redis-data` - Redis persistence
- `minio-data` - S3 object storage
- `observer-recordings` - Server Observer recordings
- `observer-long-term-storage` - Long-term storage
- `converter-hot-storage` - Server Converter hot storage

To back up your data, you can use Docker volume commands or access MinIO through its console.

## Monitoring and Operations

### Health Checks

All services include health checks. Monitor service health with:

```bash
docker compose -f infra/docker-compose.yml ps
```

Healthy services display `(healthy)` in their status. If a service shows `(unhealthy)`:

1. Check the service logs: `docker compose -f infra/docker-compose.yml logs <service-name>`
2. Verify dependencies are running
3. Check available resources (disk, memory)

### Viewing Logs

**All services:**

```bash
docker compose -f infra/docker-compose.yml logs -f
```

**Specific service:**

```bash
# Server Observer
docker compose -f infra/docker-compose.yml logs -f server-observer

# Server Converter
docker compose -f infra/docker-compose.yml logs -f server-converter

# Infrastructure
docker compose -f infra/docker-compose.yml logs -f postgres
docker compose -f infra/docker-compose.yml logs -f redis
docker compose -f infra/docker-compose.yml logs -f minio
```

### Monitoring Replay Data

**MinIO Console (Web UI):**

1. Navigate to [http://localhost:9001](http://localhost:9001)
2. Login with credentials from `.env`
3. Click on the `replays` bucket
4. Browse uploaded replay files by game ID
5. Download files directly from the browser

**PostgreSQL Queries:**

```bash
docker compose -f infra/docker-compose.yml exec postgres psql -U converter -d replays

# View replay metadata
SELECT game_id, status, created_at, updated_at 
FROM replays 
ORDER BY created_at DESC 
LIMIT 10;

# Check active recordings
SELECT game_id, created_at 
FROM replays 
WHERE status = 'recording';

# View replay statistics
SELECT 
  status, 
  COUNT(*) as count,
  MIN(created_at) as first_replay,
  MAX(created_at) as latest_replay
FROM replays 
GROUP BY status;
```

**Redis Stream Monitoring:**

```bash
docker compose -f infra/docker-compose.yml exec redis redis-cli

# View stream length
XLEN game_responses

# View recent messages
XRANGE game_responses - + COUNT 5

# View consumer group status
XINFO GROUPS game_responses

# View pending messages
XPENDING game_responses converters
```

### Performance Metrics

**Check resource usage:**

```bash
# Container resource usage
docker stats

# Specific service
docker stats server-observer server-converter
```

**Volume usage:**

```bash
# List volumes and their sizes
docker system df -v

# Check specific volume
docker volume inspect postgres-data
docker volume inspect minio-data
```

### See Also

For complete development setup instructions, see [DEVELOPMENT.md](DEVELOPMENT.md).