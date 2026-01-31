# ServerObserver Docker Build

This directory contains the Dockerfile and build script for creating a Docker image of the ServerObserver application.

## Overview

The ServerObserver is a C++ application that embeds Python and uses the `conflict_interface` Python package. The Dockerfile uses a multi-stage build approach to:

1. **Build Stage**: Compile the C++ application with all dependencies and install the Python package
2. **Runtime Stage**: Create a minimal image with only runtime dependencies

## Prerequisites

- Docker installed on your system
- The repository cloned locally

## Quick Start

1. **Navigate to the server_observer directory**:
   ```bash
   cd tools/server_observer
   ```

2. **Copy and configure the example files**:
   ```bash
   mkdir -p config
   cp config.example.json config/config.json
   cp account_pool.example.json config/account_pool.json
   # Edit config/config.json and config/account_pool.json with your settings
   ```

3. **Build and run with docker-compose**:
   ```bash
   docker-compose up --build
   ```

That's it! The ServerObserver will start and connect using your configured accounts.

## Pre-built Images

Docker images are automatically built and published to GitHub Container Registry (GHCR) on every push to the `main` branch.

### Pull from GHCR

```bash
# Pull the latest image
docker pull ghcr.io/zdox/server-observer:latest

# Run the pre-built image
docker run -v $(pwd)/config:/app ghcr.io/zdox/server-observer:latest
```

### Available Tags

- `latest` - Latest build from the main branch
- `main-<sha>` - Specific commit from main branch
- `main` - Latest from main branch

## Building the Docker Image

### Using the build script (recommended)

```bash
# Make sure the script is executable
chmod +x tools/server_observer/build_docker.sh

# From the repository root
./tools/server_observer/build_docker.sh

# Or from the tools/server_observer directory
chmod +x build_docker.sh
./build_docker.sh
```

### Custom image name and tag

```bash
./tools/server_observer/build_docker.sh --name my-observer --tag v1.0
```

### Manual build

```bash
# From the repository root
docker build -f tools/server_observer/Dockerfile -t server-observer:latest .
```

## Running the Container

### Basic usage

```bash
docker run -v $(pwd)/config:/app server-observer:latest
```

This mounts your local `config` directory to `/app` in the container where the application expects to find its configuration files.

### With custom config files

```bash
docker run -v /path/to/your/config:/app server-observer:latest server_observer /app/config.json /app/account_pool.json
```

### Interactive mode

```bash
docker run -it -v $(pwd)/config:/app server-observer:latest /bin/bash
```

## Configuration Files

The ServerObserver expects the following configuration files:

- `config.json` - Main configuration file
- `account_pool.json` - Account pool configuration

Example configuration files are provided:
- `config.example.json` - Copy this to `config.json` and customize
- `account_pool.example.json` - Copy this to `account_pool.json` and add your accounts

Mount these files into the `/app` directory in the container.

## Using Docker Compose (Recommended)

### Option 1: Build from Source

A `docker-compose.yml` file is provided for easier deployment:

```bash
# From the tools/server_observer directory
docker-compose up --build
```

This will:
- Build the Docker image from source
- Mount the `config` directory to `/app`
- Mount `recordings` and `long_term_storage` directories for persistent data
- Restart the container automatically unless stopped

### Option 2: Use Pre-built Image from GHCR

Use the `docker-compose.ghcr.yml` file to run the pre-built image:

```bash
# From the tools/server_observer directory
docker-compose -f docker-compose.ghcr.yml up
```

This will:
- Pull the latest image from GitHub Container Registry
- No build step required - faster startup
- Same volume mounts and configuration

### Managing the Service

To stop the service:
```bash
docker-compose down
```

To view logs:
```bash
docker-compose logs -f
```

## Architecture Details

### Python Integration

The application embeds Python 3.12 using pybind11. The Dockerfile ensures:

1. Python 3.12 is installed with development headers
2. The `conflict_interface` package is installed in a virtual environment at `/opt/venv`
3. The virtual environment is activated via environment variables (`VIRTUAL_ENV`, `PATH`)
4. The CMake build uses the virtual environment's Python executable

### Build Process

1. **Dependencies**: System packages (cmake, gcc, libraries) are installed
2. **Python Setup**: A virtual environment is created and the `conflict_interface` package is installed with the `tools-server-observer` extra
3. **CMake Build**: The C++ application is built, linking against the virtual environment's Python
4. **Runtime Image**: Only the compiled binary and virtual environment are copied to the final image

### Environment Variables

- `VIRTUAL_ENV=/opt/venv` - Points to the Python virtual environment
- `PATH=/opt/venv/bin:$PATH` - Ensures virtual environment binaries are used
- `PYTHONUNBUFFERED=1` - Ensures Python output is not buffered

## Troubleshooting

### Python module not found

If you get errors about missing Python modules, ensure the `conflict_interface` package and its dependencies are properly installed. The build process should handle this automatically.

### Build failures

Check that:
- Docker has enough memory (recommend 4GB+)
- You're building from the repository root
- All required files are present

### Runtime errors

If the application fails to start:
- Verify your config files are properly mounted
- Check the container logs: `docker logs <container_id>`
- Ensure the virtual environment is activated (it should be by default)

## Image Size Optimization

The multi-stage build significantly reduces the final image size by:
- Not including build tools in the runtime image
- Only copying necessary runtime dependencies
- Using Python slim image as the base

## Development

For development with live code changes, you can mount the source code:

```bash
docker run -it -v $(pwd):/src -v $(pwd)/config:/app server-observer:latest /bin/bash
```

Then rebuild inside the container as needed.

## GitHub Actions CI/CD

The repository includes a GitHub Actions workflow that automatically builds and publishes Docker images.

### Workflow Details

- **Trigger**: Automatically runs on push to `main` branch when changes are made to:
  - `tools/server_observer/**`
  - `conflict_interface/**`
  - `setup.py` or `pyproject.toml`
  - The workflow file itself
  
- **Manual Trigger**: Can also be triggered manually via workflow_dispatch

- **Output**: Images are pushed to GitHub Container Registry (GHCR) at `ghcr.io/zdox/server-observer`

### Using CI-Built Images

```bash
# Pull the latest automatically-built image
docker pull ghcr.io/zdox/server-observer:latest

# Run it
docker run -v $(pwd)/config:/app ghcr.io/zdox/server-observer:latest
```

### Workflow File

The workflow is defined in `.github/workflows/docker-build.yml` and includes:
- Docker Buildx setup for optimized builds
- Multi-platform support (linux/amd64)
- Layer caching for faster builds
- Automatic tagging with git SHA and branch name
- Push to GHCR with proper authentication

### Viewing Build Status

Check the Actions tab in the GitHub repository to see the status of Docker builds: `https://github.com/zDox/ConflictInterface/actions`
