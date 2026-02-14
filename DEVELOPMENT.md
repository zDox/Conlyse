# Development Guide

This guide explains how to set up a local development environment for debugging Server Observer and Server Converter while running the infrastructure services in Docker.

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
│  │Server Observer │ │Server        ││
│  │(Python/C++)    │ │Converter     ││
│  │                │ │(Python)      ││
│  └───────┬────────┘ └──────┬───────┘│
└──────────┼───────────────────┼────────┘
           │                   │
           │ localhost:6379    │ localhost:5432
           │ localhost:9000    │
           ▼                   ▼
┌──────────────────────────────────────┐
│  Docker (Infrastructure Services)    │
│                                      │
│  ┌──────┐  ┌──────┐  ┌────────┐    │
│  │Redis │  │Postgres MinIO   │    │
│  │:6379 │  │:5432 │  │:9000   │    │
│  └──────┘  └──────┘  └────────┘    │
└──────────────────────────────────────┘
```

## Quick Start

### Test Your Setup

After starting infrastructure services, verify everything is working:

```bash
./test-dev-env.sh
```

This script checks:
- PostgreSQL connectivity
- Redis connectivity
- MinIO S3 API
- MinIO Console
- Local data directories


### Test Your Setup

After starting infrastructure services, verify everything is working:

```bash
./test-dev-env.sh
```

This script checks:
- PostgreSQL connectivity
- Redis connectivity
- MinIO S3 API
- MinIO Console
- Local data directories


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

### 2. Verify Services

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

### 4. Run Server Converter Locally

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

### 5. Run Server Observer Locally

#### Building the C++ component:

```bash
cd tools/server_observer
mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)
```

#### Running:

```bash
# From the build directory
./server_observer ../../docker/local-dev/server-observer-config.json ../../docker/local-dev/account_pool.json
```

#### Debugging with GDB:

```bash
gdb --args ./server_observer ../../docker/local-dev/server-observer-config.json ../../docker/local-dev/account_pool.json
```

#### Debugging with IDE (CLion, VS Code with C++):

**CLion:**
1. Open `tools/server_observer` as a project
2. Configure CMake with Debug build type
3. Create Run Configuration with arguments pointing to config files
4. Set breakpoints and debug

**VS Code with C/C++ extension:**
Add to `.vscode/launch.json`:

```json
{
    "name": "Server Observer (Local Dev)",
    "type": "cppdbg",
    "request": "launch",
    "program": "${workspaceFolder}/tools/server_observer/build/server_observer",
    "args": [
        "${workspaceFolder}/docker/local-dev/server-observer-config.json",
        "${workspaceFolder}/docker/local-dev/account_pool.json"
    ],
    "stopAtEntry": false,
    "cwd": "${workspaceFolder}",
    "environment": [],
    "externalConsole": false,
    "MIMode": "gdb"
}
```

## Configuration Files

### Server Converter Config

Location: `docker/local-dev/server-converter-config.json`

Key settings for local development:
- `redis.host`: `"localhost"` (not `"redis"`)
- `database.host`: `"localhost"` (not `"postgres"`)
- `storage.s3.endpoint_url`: `"http://localhost:9000"` (not `"http://minio:9000"`)
- `storage.hot_storage_dir`: `"./data/hot_storage"` (local directory)

### Server Observer Config

Location: `docker/local-dev/server-observer-config.json`

Key settings for local development:
- `redis.host`: `"localhost"` (not `"redis"`)
- `output_dir`: `"./data/recordings"` (local directory)

### Account Pool

Location: `docker/local-dev/account_pool.json`

Add your test accounts here for development.

## Common Workflows

### Debugging a Specific Issue

1. Start infrastructure: `./stack.sh start-dev`
2. Set breakpoints in your IDE
3. Run the component in debug mode
4. Reproduce the issue
5. Step through code with debugger

### Testing Changes

1. Make code changes
2. Restart the component (no need to rebuild Docker images)
3. Test immediately
4. Iterate quickly

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

## Advanced: Running Both Modes

You can run the full production stack and development stack simultaneously by using different ports:

**For development stack**, edit `.env`:
```
POSTGRES_PORT=5433
REDIS_PORT=6380
MINIO_API_PORT=9002
MINIO_CONSOLE_PORT=9003
```

Then update your local config files to use these ports.

## Tips for Effective Debugging

1. **Use verbose logging:** Add `-v` flag or set log level to DEBUG
2. **Use Redis CLI:** Monitor the stream in real-time with `XREAD`
3. **Use PostgreSQL logs:** Watch database activity
4. **Set strategic breakpoints:** Focus on key functions
5. **Use conditional breakpoints:** Break only when specific conditions are met
6. **Inspect variables:** Use your IDE's variable inspector
7. **Step through code:** Use step-over, step-into, step-out effectively

## Next Steps

- See [DOCKER.md](DOCKER.md) for production deployment
- See [QUICK_START.md](QUICK_START.md) for quick reference
- See tool-specific documentation in `tools/server_observer/` and `tools/server_converter/`

## VS Code Setup (Ready to Use)

This repository includes pre-configured VS Code settings in `.vscode/`:

### Launch Configurations

Press F5 or use the Run panel to launch:

1. **Server Converter (Local Dev)** - Standard debugging
2. **Server Converter (Verbose)** - With verbose logging
3. **Server Observer (C++ Debug)** - C++ debugging with GDB

### Tasks

Access via Terminal > Run Task:

1. **build-server-observer-debug** - Build C++ observer in debug mode
2. **start-dev-infrastructure** - Start Docker services
3. **stop-dev-infrastructure** - Stop Docker services  
4. **test-dev-environment** - Verify setup

### Recommended Extensions

VS Code will prompt to install recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- C/C++ (ms-vscode.cpptools)
- CMake Tools (ms-vscode.cmake-tools)
- Docker (ms-azuretools.vscode-docker)
- GitLens (eamodio.gitlens)

### Quick Start in VS Code

1. Open workspace: `code /path/to/ConflictInterface`
2. Install recommended extensions (when prompted)
3. Run task: `start-dev-infrastructure`
4. Run task: `test-dev-environment`
5. Press F5 to start debugging

That's it! Everything is pre-configured.

