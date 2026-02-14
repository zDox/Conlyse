# Local Development Configuration

This directory contains configuration files for running Server Observer and Server Converter locally while using Docker infrastructure services.

## Files

- `server-observer-config.json` - Configuration for running server-observer locally
- `server-converter-config.json` - Configuration for running server-converter locally  
- `account_pool.json` - Game accounts for testing

## Usage

These configuration files are designed to work with the development Docker Compose setup (`docker-compose.dev.yml`).

### Key Differences from Docker Deployment

**Connection Hosts:**
- PostgreSQL: `localhost` instead of `postgres`
- Redis: `localhost` instead of `redis`
- MinIO: `http://localhost:9000` instead of `http://minio:9000`

**Storage Paths:**
- Use local directories (`./data/...`) instead of Docker volumes
- Allows direct access to files for debugging

### Quick Start

1. **Start infrastructure services:**
   ```bash
   ./stack.sh start-dev
   ```

2. **Create local data directories:**
   ```bash
   mkdir -p data/hot_storage
   mkdir -p data/recordings
   mkdir -p data/recordings/metadata
   ```

3. **Run Server Converter locally:**
   ```bash
   server-converter docker/local-dev/server-converter-config.json
   ```

4. **Run Server Observer locally:**
   ```bash
   # After building the C++ component
   cd tools/server_observer/build
   ./server_observer ../../../docker/local-dev/server-observer-config.json \
                     ../../../docker/local-dev/account_pool.json
   ```

## Customization

### Adding Test Accounts

Edit `account_pool.json`:

```json
{
  "accounts": [
    {
      "username": "your_test_account",
      "type": "guest",
      "enabled": true
    }
  ]
}
```

### Changing Storage Paths

Edit the config files to use different local directories:

```json
{
  "storage": {
    "hot_storage_dir": "/path/to/your/storage"
  }
}
```

### Using Different Ports

If you're running multiple instances or have port conflicts, update the ports in your `.env` file and these config files accordingly.

## Debugging Tips

1. **Use absolute paths** if you're running from different directories
2. **Check logs** - local processes write to stdout/stderr
3. **Monitor Redis** - Use `redis-cli` to watch the stream in real-time
4. **Access MinIO Console** - http://localhost:9001 to view stored files

## See Also

- [DEVELOPMENT.md](../../DEVELOPMENT.md) - Complete development guide
- [DOCKER.md](../../DOCKER.md) - Production deployment guide
