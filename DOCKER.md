# Full Stack Docker Deployment

This directory contains a complete Docker Compose setup for the entire ConflictInterface stack, including:

- **PostgreSQL** - Database for replay metadata
- **Redis** - Stream for game responses
- **MinIO** - S3-compatible object storage for replay files
- **Server Observer** - Monitors games and publishes responses to Redis
- **Server Converter** - Converts Redis streams to replay files and stores in S3

## Quick Start

### Prerequisites

- Docker 20.10 or later
- Docker Compose 2.0 or later
- At least 4GB of available RAM
- 10GB of free disk space

### Setup

1. **Copy the environment file and customize:**
   ```bash
   cp .env.example .env
   # Edit .env with your desired passwords and settings
   ```

2. **Start the entire stack:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f server-observer
   docker-compose logs -f server-converter
   ```

4. **Stop the stack:**
   ```bash
   docker-compose down
   ```

5. **Stop and remove all data:**
   ```bash
   docker-compose down -v
   ```

## Service Access

After starting the stack, you can access:

- **MinIO Console**: http://localhost:9001
  - Username: `minioadmin` (or value from `.env`)
  - Password: `minioadmin` (or value from `.env`)
  
- **PostgreSQL**: `localhost:5432`
  - Database: `replays`
  - Username: `converter` (or value from `.env`)
  - Password: `changeme` (or value from `.env`)
  
- **Redis**: `localhost:6379`

## Configuration

### Server Observer Configuration

Edit `docker/server-observer-config/config.json` to customize:
- Recording settings
- Redis connection
- Game finder settings

Edit `docker/server-observer-config/account_pool.json` to add game accounts for observation.

### Server Converter Configuration

Edit `docker/server-converter-config/config.json` to customize:
- Redis consumer settings
- Database connection
- S3 storage settings
- Batch processing parameters

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

## Monitoring

### Health Checks

All services have health checks configured. Check service health with:

```bash
docker-compose ps
```

Healthy services will show `(healthy)` in their status.

### Viewing Replay Data

**MinIO Console:**
1. Open http://localhost:9001
2. Login with credentials from `.env`
3. Navigate to the `replays` bucket
4. View uploaded replay files

**PostgreSQL Database:**
```bash
docker-compose exec postgres psql -U converter -d replays

# View replay metadata
SELECT * FROM replays;

# View active recordings
SELECT * FROM replays WHERE status = 'recording';
```

**Redis Stream:**
```bash
docker-compose exec redis redis-cli

# View stream length
XLEN game_responses

# View recent entries
XRANGE game_responses - + COUNT 10
```

## Troubleshooting

### Service won't start

1. Check logs: `docker-compose logs <service-name>`
2. Verify all dependencies are healthy: `docker-compose ps`
3. Check available disk space: `df -h`

### MinIO bucket not created

The `minio-init` service creates the bucket on startup. Check its logs:
```bash
docker-compose logs minio-init
```

If it failed, you can manually create the bucket:
1. Access MinIO Console at http://localhost:9001
2. Create a bucket named `replays`
3. Set download policy for the bucket

### Server Converter can't connect to PostgreSQL

Wait for PostgreSQL to be fully healthy before starting:
```bash
docker-compose up -d postgres
# Wait for healthy status
docker-compose up -d server-converter
```

### Out of disk space

Remove old Docker resources:
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (WARNING: This deletes data!)
docker volume prune
```

## Scaling

### Multiple Server Converters

You can run multiple server converter instances for high availability:

```bash
docker-compose up -d --scale server-converter=3
```

Each instance will have a unique consumer name in the Redis consumer group, ensuring messages are distributed across instances.

### Resource Limits

To set resource limits, add to each service in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      memory: 512M
```

## Development

### Rebuilding Images

After code changes, rebuild images:

```bash
docker-compose build
docker-compose up -d
```

Or rebuild a specific service:

```bash
docker-compose build server-observer
docker-compose up -d server-observer
```

### Using Pre-built Images

To use pre-built images from GitHub Container Registry instead of building locally, edit `docker-compose.yml` and replace the `build` sections with:

```yaml
server-observer:
  image: ghcr.io/zdox/server-observer:latest
  # Remove the build section

server-converter:
  image: ghcr.io/zdox/server-converter:latest
  # Remove the build section
```

## Security Notes

- **Change default passwords** in `.env` before production use
- MinIO credentials should be strong passwords
- PostgreSQL password should be strong
- Consider using Docker secrets for sensitive data in production
- Limit network exposure by not publishing unnecessary ports

## Production Deployment

For production deployments:

1. Use strong passwords in `.env`
2. Enable SSL/TLS for MinIO, PostgreSQL, and Redis
3. Set up proper backup strategies for volumes
4. Configure log rotation
5. Set up monitoring and alerting
6. Use Docker secrets instead of environment variables
7. Consider using Docker Swarm or Kubernetes for orchestration

## License

See the main repository LICENSE file.
