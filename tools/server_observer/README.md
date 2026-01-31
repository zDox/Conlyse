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

See [CMakeLists.txt](CMakeLists.txt) for build requirements.

```bash
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

## Documentation

- [DOCKER.md](DOCKER.md) - Complete Docker build and deployment guide
- [CMakeLists.txt](CMakeLists.txt) - Build configuration
- Example configs:
  - [config.example.json](config.example.json) - Application configuration template
  - [account_pool.example.json](account_pool.example.json) - Account credentials template
