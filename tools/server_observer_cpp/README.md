# ServerObserver C++ Implementation

This is a complete C++ rewrite of the ServerObserver tool for lightweight recording of server responses across multiple games.

## Key Features

- **Python Integration**: Uses the Python HubInterface ONLY for authentication and retrieving auth data
- **Pure C++**: All other functionality (HTTP requests, JSON parsing, compression, threading) is implemented in C++
- **High Performance**: Leverages C++ for efficient concurrent game observation
- **External Dependencies**:
  - cpp-httplib: HTTP client
  - nlohmann/json: JSON parsing
  - zstd: Compression
  - OpenSSL: SHA1 hashing
  - Python 3.12+: For HubInterface authentication only

## Architecture

### Components

1. **HubInterfaceWrapper** (`hub_interface_wrapper.cpp`): 
   - Thin wrapper around Python's HubInterface
   - Used ONLY for login and retrieving authentication data
   - All actual game observation is done in C++

2. **ServerObserver** (`server_observer.cpp`):
   - Main orchestrator managing multiple game observations
   - Handles game scanning, session scheduling, and thread pooling

3. **ObservationSession** (`observation_session.cpp`):
   - Manages individual game observation sessions
   - Creates short-lived workers for each update

4. **ObservationApi** (`observation_api.cpp`):
   - Handles HTTP API calls to game servers in C++
   - Pure C++ implementation using cpp-httplib

5. **Account & AccountPool** (`account.cpp`, `account_pool.cpp`):
   - Manages authentication accounts and proxy assignments
   - Loads accounts from JSON configuration

6. **RecordingRegistry** (`recording_registry.cpp`):
   - Tracks recording status (active, completed, failed)
   - Persists state to JSON file

7. **RecordingStorage** (`recording_storage.cpp`):
   - Handles file storage with zstd compression
   - Supports file rotation to long-term storage

8. **StaticMapCache** (`static_map_cache.cpp`):
   - Caches static map data to avoid duplicate downloads

## Building

### Prerequisites

```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    libzstd-dev \
    libssl-dev \
    python3-dev \
    pkg-config
```

### Build Steps

```bash
cd tools/server_observer_cpp
mkdir -p build
cd build
cmake ..
make -j$(nproc)
```

The compiled binary will be located at `build/server_observer`.

### Installation

```bash
# From the build directory
sudo make install
```

This will install the `server_observer` binary to `/usr/local/bin/`.

## Usage

### Configuration

Create a `config.json` file with your observation settings:

```json
{
    "scenario_ids": [6, 8, 18],
    "max_parallel_recordings": 5,
    "max_parallel_updates": 10,
    "max_parallel_first_updates": 5,
    "scan_interval": 30,
    "update_interval": 60,
    "output_dir": "./recordings",
    "output_metadata_dir": "./metadata",
    "enabled_scanning": true,
    "max_guest_games_per_account": 3,
    "long_term_storage_path": "/path/to/long_term_storage",
    "file_size_threshold": 104857600,
    "registry_path": "./server_observer_registry.json"
}
```

### Account Pool Configuration

Create an `account_pool.json` file:

```json
{
    "WEBSHARE_API_TOKEN": "your_webshare_token_here",
    "accounts": [
        {
            "username": "account1",
            "password": "password1",
            "email": "email1@example.com",
            "proxy_id": "proxy_id_1",
            "proxy_url": "socks5://user:pass@host:port"
        }
    ]
}
```

### Running

```bash
./server_observer config.json account_pool.json
```

Or if installed:

```bash
server_observer config.json account_pool.json
```

## Output

The tool generates the following files for each game:

### In `output_dir/game_{game_id}/`:
- `responses.jsonl.zst`: Compressed JSON lines of server responses
- `requests.jsonl.zst`: Compressed JSON lines of requests (if enabled)
- `game_states.bin`: Binary game state snapshots
- `static_map_data.bin`: Compressed static map data

### In `output_metadata_dir/game_{game_id}/` (if configured):
- `metadata.json`: Recording metadata including timestamps
- `recording.log`: Detailed log of the recording session
- `library.log`: ConflictInterface library logs

### In Long-term Storage (if configured):
When response files exceed the configured threshold, they are rotated to long-term storage with sequential naming (`responses_0001.jsonl.zst`, `responses_0002.jsonl.zst`, etc.).

## Key Differences from Python Version

1. **Authentication**: Python HubInterface is used ONLY for login, not for game operations
2. **HTTP Client**: Pure C++ using cpp-httplib instead of Python httpx
3. **Concurrency**: Native C++ threads instead of Python threading
4. **Performance**: Significantly faster due to compiled nature and efficient memory management
5. **Dependencies**: Minimal external dependencies, all C++ libraries

## Development

### Adding New Features

1. Update the appropriate header file in `include/`
2. Implement the feature in the corresponding `.cpp` file in `src/`
3. Rebuild using `make`

### Debugging

Build with debug symbols:

```bash
cmake -DCMAKE_BUILD_TYPE=Debug ..
make
```

Use with gdb:

```bash
gdb ./server_observer
```

## Troubleshooting

### Python Import Errors

If you see errors about missing Python modules:
- Ensure ConflictInterface is installed: `pip install -e .`
- Check Python path is correctly set in `hub_interface_wrapper.cpp`

### Linking Errors

If you encounter linking errors:
- Ensure all required libraries are installed
- Check CMakeLists.txt for correct library names
- Try rebuilding from scratch: `rm -rf build && mkdir build && cd build && cmake .. && make`

### Authentication Failures

If accounts fail to authenticate:
- Verify credentials in `account_pool.json`
- Check proxy connectivity
- Ensure WebShare token is valid and proxies are active

## License

MIT License - Same as the main ConflictInterface project
