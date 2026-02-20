# ConflictInterface Full Stack Deployment

This guide explains how to deploy the complete ConflictInterface stack using Docker Compose. The stack provides an automated system for recording and storing game replays.

## Overview

The deployment includes five main components:

- **PostgreSQL** - Database for replay metadata and tracking
- **Redis** - Message stream for real-time game response data
- **MinIO** - S3-compatible object storage for replay files
- **Server Observer** - Monitors live games and captures responses
- **Server Converter** - Processes responses and creates replay files


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
```

**Security Note:** Use strong, unique passwords for production deployments.

### 2. Configure Services

#### Server Observer Configuration

Edit `docker/prod/server-observer-config.json`:

```json
{
  "recording_settings": {
    "enable_recording": true,
    "output_directory": "/recordings"
  },
  "redis": {
    "host": "redis",
    "port": 6379,
    "stream_name": "game_responses"
  },
  "game_finder": {
    "check_interval_seconds": 60
  }
}
```

Add game accounts to `docker/prod/account_pool.json`:

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

Edit `docker/prod/server-converter-config.json`:

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
docker-compose up -d

# Check service status
docker-compose ps

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f server-observer
docker-compose logs -f server-converter
```

### 4. Verify Deployment

Check that all services are healthy:

```bash
docker-compose ps
```

All services should show `(healthy)` status within 1-2 minutes.

### 5. Initial Setup Verification

Verify the MinIO bucket was created:

```bash
docker-compose logs minio-init
```

You should see: "Bucket 'replays' created successfully"

Check PostgreSQL connectivity:

```bash
docker-compose exec postgres psql -U converter -d replays
# Inside PostgreSQL shell:
\dt  # List tables
\q   # Quit
```

Check Redis stream:

```bash
docker-compose exec redis redis-cli
# Inside Redis CLI:
INFO
QUIT
```

## Accessing Deployed Services

Once the stack is running, you can access the various services:

### MinIO Console (S3 Storage)

- **URL**: http://localhost:9001
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
docker-compose exec postgres psql -U converter -d replays
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
docker-compose exec redis redis-cli
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
┌──────┐  ┌─────────┐
│Postgres│ │ MinIO │──> Stores replays
│  DB    │ │  (S3) │
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
docker-compose ps
```

Healthy services display `(healthy)` in their status. If a service shows `(unhealthy)`:

1. Check the service logs: `docker-compose logs <service-name>`
2. Verify dependencies are running
3. Check available resources (disk, memory)

### Viewing Logs

**All services:**
```bash
docker-compose logs -f
```

**Specific service:**
```bash
# Server Observer
docker-compose logs -f server-observer

# Server Converter
docker-compose logs -f server-converter

# Infrastructure
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f minio
```

### Monitoring Replay Data

**MinIO Console (Web UI):**
1. Navigate to http://localhost:9001
2. Login with credentials from `.env`
3. Click on the `replays` bucket
4. Browse uploaded replay files by game ID
5. Download files directly from the browser

**PostgreSQL Queries:**
```bash
docker-compose exec postgres psql -U converter -d replays

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
docker-compose exec redis redis-cli

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

## Troubleshooting

### Service Won't Start

**Symptoms:** Service repeatedly restarts or fails to start

**Solutions:**

1. **Check service logs:**
   ```bash
   docker-compose logs <service-name>
   ```

2. **Verify dependencies are healthy:**
   ```bash
   docker-compose ps
   ```
   Ensure PostgreSQL, Redis, and MinIO are healthy before starting observers/converters.

3. **Check available resources:**
   ```bash
   # Disk space
   df -h
   
   # Memory usage
   free -h
   
   # Docker resources
   docker system df
   ```

4. **Restart in correct order:**
   ```bash
   # Stop all services
   docker-compose down
   
   # Start infrastructure first
   docker-compose up -d postgres redis minio
   
   # Wait for health checks, then start applications
   sleep 10
   docker-compose up -d server-observer server-converter
   ```

### MinIO Bucket Not Created

**Symptoms:** Server Converter can't upload files, S3 errors in logs

**Solutions:**

1. **Check minio-init service logs:**
   ```bash
   docker-compose logs minio-init
   ```

2. **Manually create bucket:**
   - Open MinIO Console: http://localhost:9001
   - Login with credentials from `.env`
   - Click "Create Bucket"
   - Name it `replays`
   - Set Access Policy to "Public" or configure as needed

3. **Restart minio-init service:**
   ```bash
   docker-compose up minio-init
   ```

### Server Converter Can't Connect to PostgreSQL

**Symptoms:** Connection refused, authentication failed

**Solutions:**

1. **Verify PostgreSQL is healthy:**
   ```bash
   docker-compose ps postgres
   ```

2. **Check credentials match:**
   Compare `.env` file with `docker/server-converter-config/config.json`:
   - Database user
   - Database password
   - Database name

3. **Test connection manually:**
   ```bash
   docker-compose exec postgres psql -U converter -d replays
   ```

4. **Ensure network connectivity:**
   ```bash
   docker-compose exec server-converter ping postgres
   ```

### Redis Connection Issues

**Symptoms:** Server Observer/Converter can't connect to Redis

**Solutions:**

1. **Check Redis is running:**
   ```bash
   docker-compose ps redis
   docker-compose logs redis
   ```

2. **Test Redis connection:**
   ```bash
   docker-compose exec redis redis-cli ping
   # Should return: PONG
   ```

3. **Verify stream exists:**
   ```bash
   docker-compose exec redis redis-cli XLEN game_responses
   ```

### Out of Disk Space

**Symptoms:** Services crash, writes fail, unhealthy status

**Solutions:**

1. **Check disk usage:**
   ```bash
   df -h
   docker system df -v
   ```

2. **Clean up Docker resources:**
   ```bash
   # Remove stopped containers
   docker container prune
   
   # Remove unused images
   docker image prune -a
   
   # Remove unused volumes (WARNING: Deletes data!)
   docker volume prune
   ```

3. **Clean up old replay files:**
   - Access MinIO Console
   - Delete old replays from the bucket
   - Or use lifecycle policies

### Server Observer Not Finding Games

**Symptoms:** No game responses in Redis stream

**Solutions:**

1. **Check account pool:**
   Verify `docker/server-observer-config/account_pool.json` has valid accounts

2. **Review observer logs:**
   ```bash
   docker-compose logs -f server-observer
   ```

3. **Verify game finder settings:**
   Check `check_interval_seconds` in config.json isn't too high

### Container Memory Issues

**Symptoms:** OOMKilled errors, services crashing randomly

**Solutions:**

1. **Increase Docker memory limit:**
   - Docker Desktop: Settings → Resources → Memory
   - Recommended: At least 4GB

2. **Add memory limits to docker-compose.yml:**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 2G
   ```

3. **Monitor memory usage:**
   ```bash
   docker stats
   ```

## Scaling the Deployment

### Horizontal Scaling

#### Multiple Server Converters

Run multiple converter instances for high availability and increased throughput:

```bash
# Scale to 3 converter instances
docker-compose up -d --scale server-converter=3

# Verify all instances are running
docker-compose ps server-converter
```

Each converter instance:
- Has a unique consumer name in the Redis consumer group
- Processes messages independently
- Shares the workload automatically
- Provides redundancy if one fails

**When to scale converters:**
- Redis stream is growing (backlog building up)
- High game activity periods
- Need for high availability

#### Multiple Server Observers

Scale observers to monitor more games simultaneously:

```bash
# Scale to 2 observer instances
docker-compose up -d --scale server-observer=2
```

**Considerations:**
- Each observer needs accounts from the account pool
- Observers will divide available games between them
- More observers = more concurrent game monitoring

### Vertical Scaling
#### Database Performance

For high-load scenarios, tune PostgreSQL:

```yaml
postgres:
  environment:
    # Add to existing environment
    POSTGRES_MAX_CONNECTIONS: 100
    POSTGRES_SHARED_BUFFERS: 256MB
    POSTGRES_WORK_MEM: 16MB
```

#### Redis Performance

For large streams, configure Redis memory and persistence:

```yaml
redis:
  command: >
    redis-server
    --maxmemory 1gb
    --maxmemory-policy allkeys-lru
    --save 60 1000
```

### Load Balancing

For production deployments with multiple converters:

1. **Consumer Group Distribution:** Redis automatically distributes messages across converter instances in the consumer group

2. **Database Connection Pooling:** Each converter maintains its own connection pool to PostgreSQL

3. **S3 Upload Parallelization:** Multiple converters upload to MinIO simultaneously

### Monitoring Scaling Performance

**Check converter lag:**
```bash
docker-compose exec redis redis-cli XPENDING game_responses converters

# View message distribution across consumers
docker-compose exec redis redis-cli XINFO CONSUMERS game_responses converters
```

**Monitor resource usage:**
```bash
# Real-time stats
docker stats

# Specific services
docker stats server-converter server-observer
```

**Database connection count:**
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U converter -d replays
```

Then run this SQL query:
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'replays';
```


## Production Deployment

For production deployments:

1. Use strong passwords in `.env`
2. Enable SSL/TLS for MinIO, PostgreSQL, and Redis
3. Set up proper backup strategies for volumes
4. Configure log rotation
5. Set up monitoring and alerting
6. Use Docker secrets instead of environment variables
7. Consider using Docker Swarm or Kubernetes for orchestration

### See Also

For complete development setup instructions, see [DEVELOPMENT.md](DEVELOPMENT.md).


