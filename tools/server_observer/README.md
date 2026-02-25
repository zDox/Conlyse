# ServerObserver

C++ application that observes and records Conflict of Nations games.

## ⚠️ Configuration Required

**Before running, you MUST create configuration files:**

```bash
# Copy example files
cp config.example.json config.json
cp account_pool.example.json account_pool.json

# Edit with your credentials
nano config.json
nano account_pool.json
```

**Important:** These config files contain sensitive credentials and are:
- ✅ Excluded from git (in `.gitignore`)
- ✅ Excluded from Docker images (in `.dockerignore`)
- ❌ Never committed to version control
- ❌ Never embedded in Docker images

## S3 Storage Configuration

ServerObserver can upload static map data to S3-compatible storage (e.g., Hetzner Object Storage, AWS S3, MinIO). This allows sharing static map data with the server converter and other services.

To enable S3 uploads for static map data, configure the following in your `config.json`:

```json
{
  "storage": {
    "recordings_dir": "/app/recordings",
    "long_term_storage_dir": "/app/long_term_storage",
    "static_maps_dir": "/app/static_maps",
    "s3_enabled": true,
    "s3": {
      "endpoint_url": "https://your-s3-endpoint.com",
      "access_key": "your-access-key",
      "secret_key": "your-secret-key",
      "bucket_name": "replays",
      "region": "us-east-1"
    }
  }
}
```

When `s3_enabled` is `true`, static map data will be:
1. Saved locally to `static_maps_dir` (compressed with zstd)
2. Automatically uploaded to S3 at `static_maps/map_{map_id}.bin`

This should use the **same S3 configuration** as the server converter to ensure both services can access the static map data.

## Running with Docker

See [DOCKER.md](DOCKER.md) for complete Docker documentation.

**Quick start:**
```bash
# Create config directory
mkdir -p config
cp config.example.json config/config.json
cp account_pool.example.json config/account_pool.json
# Edit config files...

# Run with docker-compose
docker-compose up --build
```

**The config files are mounted as volumes** - they are NOT built into the image.

**SELinux users (Fedora, RHEL, CentOS):** If you get permission errors, add `:z` to volume mounts or see [DOCKER.md](DOCKER.md) troubleshooting section.

## Building from Source

### System Requirements

The following system packages are required:

```bash
# Ubuntu/Debian
sudo apt-get install build-essential cmake git pkg-config \
    libzstd-dev zlib1g-dev libssl-dev libcurl4-openssl-dev \
    libcurlpp-dev libxml2-dev python3-dev

# Fedora/RHEL
sudo dnf install gcc-c++ cmake git pkg-config \
    libzstd-devel zlib-devel openssl-devel libcurl-devel \
    curlpp-devel libxml2-devel python3-devel
```

All other dependencies (MinIO C++ SDK, pybind11, nlohmann/json, etc.) are automatically downloaded and built by CMake using FetchContent.

### Build Steps

```bash
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

See [CMakeLists.txt](CMakeLists.txt) for complete build configuration.

## Documentation

- [DOCKER.md](DOCKER.md) - Complete Docker build and deployment guide
- [MINIO_MIGRATION.md](MINIO_MIGRATION.md) - MinIO C++ SDK migration details
- [CMakeLists.txt](CMakeLists.txt) - Build configuration
- Example configs:
  - [config.example.json](config.example.json) - Application configuration template
  - [account_pool.example.json](account_pool.example.json) - Account credentials template
