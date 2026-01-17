# Server Observer

The Server Observer is a lightweight tool for recording server responses across multiple games concurrently.

## Features

- **Multi-game observation**: Observe multiple games simultaneously
- **Automatic game scanning**: Automatically discover and join new games based on scenario IDs
- **Response recording**: Record all server responses to compressed files
- **Long-term storage**: Automatically rotate large response files to long-term storage
- **Account pooling**: Use multiple accounts to distribute observation load
- **Resume capability**: Resume observations across restarts

## Configuration

The Server Observer is configured via a JSON configuration file. See `examples/server_observer_config_example.json` for a complete example.

### Basic Configuration

```json
{
  "scenario_ids": [5975, 5976],
  "max_parallel_recordings": 5,
  "max_parallel_updates": 10,
  "scan_interval": 30,
  "update_interval": 60.0,
  "output_dir": "./recordings",
  "account_pool_path": "./account_pool.json"
}
```

### Configuration Options

#### Required Options

- `scenario_ids`: List of scenario IDs to observe
- `output_dir`: Directory where recordings will be saved

#### Optional Options

- `max_parallel_recordings`: Maximum number of games to record simultaneously (default: 1)
- `max_parallel_updates`: Maximum number of concurrent update requests (default: 1)
- `max_parallel_first_updates`: Maximum number of concurrent first update requests (default: 1)
- `scan_interval`: Seconds between scans for new games (default: 30)
- `update_interval`: Seconds between game state updates (default: 60.0)
- `output_metadata_dir`: Separate directory for metadata files (default: same as `output_dir`)
- `enabled_scanning`: Enable automatic game scanning (default: true)
- `max_guest_games_per_account`: Maximum guest games per account (default: unlimited)
- `account_pool_path`: Path to account pool JSON file
- `WEBSHARE_API_TOKEN`: API token for Webshare proxy service

### Long-Term Storage Configuration

The Server Observer supports automatic rotation of large response files to long-term storage. This is useful for managing disk space when recording long-running games that generate large amounts of data.

#### Configuration Options

- `long_term_storage_path`: Path to the long-term storage directory
- `file_size_threshold`: Size threshold in bytes for rotating files

When both options are set, the Server Observer will:
1. Monitor the size of the current response file before each write
2. When the file exceeds the threshold, move it to long-term storage
3. Create a new response file and continue recording
4. Maintain the same directory structure in long-term storage as in the output directory

#### Example Configuration

```json
{
  "output_dir": "./recordings",
  "long_term_storage_path": "./long_term_storage",
  "file_size_threshold": 104857600
}
```

This configuration will:
- Record responses to `./recordings/game_12345/responses.jsonl.zst`
- When the file exceeds 100 MB (104857600 bytes), move it to `./long_term_storage/game_12345/responses_0001.jsonl.zst`
- Create a new `./recordings/game_12345/responses.jsonl.zst` and continue recording
- Subsequent rotations will be numbered sequentially: `responses_0002.jsonl.zst`, `responses_0003.jsonl.zst`, etc.

#### File Size Threshold Examples

- 10 MB: `10485760` bytes
- 50 MB: `52428800` bytes
- 100 MB: `104857600` bytes
- 500 MB: `524288000` bytes
- 1 GB: `1073741824` bytes

### Directory Structure

#### Without Long-Term Storage

```
output_dir/
├── game_12345/
│   ├── responses.jsonl.zst
│   ├── static_map_data.bin
│   ├── metadata.json
│   └── recording.log
└── game_67890/
    ├── responses.jsonl.zst
    ├── static_map_data.bin
    ├── metadata.json
    └── recording.log
```

#### With Long-Term Storage

```
output_dir/
├── game_12345/
│   ├── responses.jsonl.zst          (current recording)
│   ├── static_map_data.bin
│   ├── metadata.json
│   └── recording.log
└── game_67890/
    ├── responses.jsonl.zst
    ├── static_map_data.bin
    ├── metadata.json
    └── recording.log

long_term_storage/
├── game_12345/
│   ├── responses_0001.jsonl.zst    (rotated files)
│   ├── responses_0002.jsonl.zst
│   └── responses_0003.jsonl.zst
└── game_67890/
    └── responses_0001.jsonl.zst
```

## Usage

Run the Server Observer with a configuration file:

```bash
server-observer config.json
```

Or if running from source:

```bash
python -m tools.server_observer config.json
```

## Output Files

For each observed game, the following files are created:

- `responses.jsonl.zst`: Compressed responses from the game server
- `static_map_data.bin`: Compressed static map data
- `metadata.json`: Recording metadata including timestamps and rotation history
- `recording.log`: Server Observer tool log

When using long-term storage, rotated response files are moved to the long-term storage directory with sequential numbering.

## Account Pool

The Server Observer can use multiple accounts to distribute the observation load. Create an `account_pool.json` file with the following structure:

```json
{
  "accounts": [
    {
      "username": "user1",
      "password": "pass1"
    },
    {
      "username": "user2",
      "password": "pass2"
    }
  ]
}
```

## Resuming Observations

The Server Observer automatically resumes active observations when restarted. It maintains a registry of active observations in `server_observer_registry.json`.
