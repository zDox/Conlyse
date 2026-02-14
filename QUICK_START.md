# Quick Reference: Docker Stack

## Start/Stop
```bash
./stack.sh start    # Start all services
./stack.sh stop     # Stop all services
./stack.sh status   # Check health
```

## View Logs
```bash
./stack.sh logs              # All services
./stack.sh logs-observer     # Server Observer only
./stack.sh logs-converter    # Server Converter only
```

## Access Services
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **PostgreSQL**: `./stack.sh shell-postgres`
- **Redis**: `./stack.sh shell-redis`

## Check Data
```bash
# PostgreSQL - View replays
./stack.sh shell-postgres
SELECT * FROM replays LIMIT 10;

# Redis - View stream
./stack.sh shell-redis
XLEN game_responses
XRANGE game_responses - + COUNT 5
```

## Troubleshooting
```bash
# Service won't start
./stack.sh logs-[service]    # Check logs
./stack.sh status             # Check health

# Restart specific service
./stack.sh restart-observer
./stack.sh restart-converter

# Complete reset (DELETES DATA!)
./stack.sh reset
```

## Development
```bash
# Rebuild after code changes
./stack.sh build
./stack.sh restart

# Or rebuild specific service
./stack.sh build-observer
./stack.sh restart-observer
```

## Data Location
All data is stored in Docker volumes:
- `postgres-data` - Database
- `redis-data` - Redis persistence
- `minio-data` - S3 storage
- `observer-recordings` - Recordings
- `converter-hot-storage` - Active replays

## Configuration Files
- `docker/server-observer-config/config.json` - Observer settings
- `docker/server-observer-config/account_pool.json` - Game accounts
- `docker/server-converter-config/config.json` - Converter settings
- `.env` - Environment variables (passwords, ports)

## First Time Setup
1. `cp .env.example .env` - Create environment file
2. Edit `docker/server-observer-config/account_pool.json` - Add accounts
3. Edit `.env` - Change passwords
4. `./stack.sh start` - Start services
5. `./stack.sh status` - Verify all healthy

## Architecture
```
Game → Server Observer → Redis → Server Converter → PostgreSQL + MinIO
                                                          ↓
                                                   Replay Files (S3)
```

## Development Mode

For debugging with your IDE:

```bash
# Start infrastructure only
./stack.sh start-dev

# Run observer/converter locally
server-converter docker/local-dev/server-converter-config.json

# See DEVELOPMENT.md for full guide
```
