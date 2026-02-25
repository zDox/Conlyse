# Development Guide

This guide explains how to set up a local development environment for debugging Server Observer and Server Converter while running the infrastructure services in Docker.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Running Components Locally](#running-components-locally)
  - [Server Converter](#server-converter)
  - [Server Observer](#server-observer)
- [Configuration Files](#configuration-files)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)
- [Stopping Services](#stopping-services)

## Overview

The development setup allows you to:
- Run PostgreSQL, Redis, and MinIO in Docker containers
- Run Server Observer and Server Converter locally from your IDE
- Debug with breakpoints and full IDE features
- Have infrastructure services accessible on localhost

## Architecture

```
┌──────────────────────────────────────┐
│  Your IDE / Local Development        │
│                                      │
│  ┌────────────────┐ ┌──────────────┐│
│  │Server Observer │ │   Server     ││
│  │(Python/C++)    │ │  Converter   ││
│  │                │ │  (Python)    ││
│  └───────┬────────┘ └──────┬───────┘│
└──────────┼───────────────────┼────────┘
           │                   │
           │ localhost:6379    │ localhost:5432
           │ localhost:9000    │
           ▼                   ▼
┌──────────────────────────────────────┐
│  Docker (Infrastructure Services)    │
│                                      │
│  ┌──────┐  ┌──────────┐  ┌────────┐ │
│  │Redis │  │PostgreSQL│  │ MinIO  │ │
│  │:6379 │  │  :5432   │  │ :9000  │ │
│  └──────┘  └──────────┘  └────────┘ │
└──────────────────────────────────────┘
```

## Quick Start

### 1. Start Infrastructure Services

```bash
# Start only PostgreSQL, Redis, and MinIO
docker compose -f docker-compose.dev.yml up -d

# Check that all services are healthy
docker compose -f docker-compose.dev.yml ps
```

Or using the stack script:

```bash
./stack.sh start-dev
```

### 2. Verify Services Manually (Optional)

```bash
# Test PostgreSQL connection
docker compose -f docker-compose.dev.yml exec postgres psql -U converter -d replays -c "SELECT version();"

# Test Redis connection
docker compose -f docker-compose.dev.yml exec redis redis-cli ping

# Access MinIO Console
# Open http://localhost:9001 in your browser
# Login: minioadmin / minioadmin
```

### 3. Set Up Local Data Directories

```bash
# Create local directories for data storage
mkdir -p data/hot_storage
mkdir -p data/recordings
mkdir -p data/recordings/metadata
```

## Running Components Locally

### Server Converter

#### Using Python directly:

```bash
# Install the package in development mode
pip install -e ".[tools-server-converter]"

# Run the server converter
server-converter docker/local-dev/server-converter-config.json
```

#### Using your IDE (PyCharm, VS Code, etc.):

**PyCharm:**
1. Create a new Run Configuration
   - Script path: `tools/server_converter/__main__.py`
   - Parameters: `docker/local-dev/server-converter-config.json`
   - Python interpreter: Your virtual environment
   - Working directory: Repository root

2. Set breakpoints in the code
3. Run in Debug mode (Shift+F9)

**VS Code:**
Add to `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Server Converter (Local Dev)",
            "type": "python",
            "request": "launch",
            "module": "tools.server_converter",
            "args": [
                "docker/local-dev/server-converter-config.json"
            ],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

### Server Observer

The primary implementation of Server Observer is now the Rust crate in `tools/server_observer_rust`.

#### Building the Rust observer

```bash
cd tools/server_observer_rust
cargo build
```

#### Running locally

The Rust binary accepts an optional **TOML** config file path and an optional `account_pool.json` path:

```bash
# From repository root, using a TOML config
cargo run -p server_observer -- \
    docker/dev/server-observer-config.toml \
    docker/dev/account_pool.json
```

If no arguments are provided, it defaults to `config.toml` and `account_pool.json` in the working directory. See `tools/server_observer_rust/README.md` and `config.example.toml` for more details.

## Configuration Files

### Server Converter Config

Location: `docker/local-dev/server-converter-config.json`

Key settings for local development:
- `redis.host`: `"localhost"` (not `"redis"`)
- `database.host`: `"localhost"` (not `"postgres"`)
- `storage.s3.endpoint_url`: `"http://localhost:9000"` (not `"http://minio:9000"`)
- `storage.hot_storage_dir`: `"./data/hot_storage"` (local directory)

### Server Observer Config

Location: `docker/dev/server-observer-config.toml`

Key settings for local development:
- `redis.host`: `"localhost"` (not `"redis"`)
- `output_dir`: `"./data/recordings"` (local directory)

### Account Pool

Location: `docker/local-dev/account_pool.json`

Add your test accounts here for development.

## Common Workflows
### Viewing Data

**PostgreSQL:**
```bash
# Connect to database
docker compose -f docker-compose.dev.yml exec postgres psql -U converter -d replays

# View replays
SELECT * FROM replays ORDER BY created_at DESC LIMIT 10;
```

**Redis:**
```bash
# Connect to Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli

# View stream
XLEN game_responses
XRANGE game_responses - + COUNT 5
```

**MinIO:**
- Open http://localhost:9001
- Login: minioadmin / minioadmin
- Browse the `replays` bucket

## Troubleshooting

### Cannot connect to PostgreSQL

**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
- Verify PostgreSQL is running: `docker compose -f docker-compose.dev.yml ps`
- Check port is exposed: `docker compose -f docker-compose.dev.yml port postgres 5432`
- Verify credentials in `.env` match your config file

### Cannot connect to Redis

**Problem:** `redis.exceptions.ConnectionError: Error connecting to localhost:6379`

**Solution:**
- Verify Redis is running: `docker compose -f docker-compose.dev.yml ps`
- Check port: `docker compose -f docker-compose.dev.yml port redis 6379`
- Test with redis-cli: `docker compose -f docker-compose.dev.yml exec redis redis-cli ping`

### MinIO S3 operations fail

**Problem:** `botocore.exceptions.EndpointConnectionError`

**Solution:**
- Verify MinIO is running: `docker compose -f docker-compose.dev.yml ps`
- Check bucket exists: Open http://localhost:9001 and verify `replays` bucket
- Verify credentials match in config: `minioadmin` / `minioadmin`

### Permission denied on data directories

**Problem:** Cannot write to `./data/hot_storage` or `./data/recordings`

**Solution:**
```bash
# Create directories with correct permissions
mkdir -p data/hot_storage data/recordings data/recordings/metadata
chmod -R 755 data/
```

### Database tables don't exist

**Problem:** `psycopg2.errors.UndefinedTable: relation "replays" does not exist`

**Solution:**
The Server Converter creates tables automatically on first run. Make sure:
1. PostgreSQL is accessible
2. Database credentials are correct
3. Run the converter once to initialize schema

## Stopping Services

```bash
# Stop infrastructure services
docker compose -f docker-compose.dev.yml down

# Or using stack script
./stack.sh stop-dev

# Stop and remove volumes (deletes all data!)
docker compose -f docker-compose.dev.yml down -v
```