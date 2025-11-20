# Record to Replay Converter CLI Tool

A command-line tool for converting recorder data to replay format in Conflict Interface.

## Overview

The Record to Replay Converter transforms recording data (created by the `recorder` tool) into replay files that can be used with the replay system. This allows you to:
- Convert compressed game state recordings into replay databases
- Enable time travel through recorded game sessions
- Use the replay debug tools on converted recordings
- Share recordings in a format that supports bidirectional navigation

## Installation

The converter is installed automatically when you install the conflict-interface package:

```bash
pip install -e .
```

This will create a `record-to-replay` command-line tool.

## Usage

### Basic Usage

```bash
record-to-replay <recording_dir> <output_file>
```

### Arguments

- `recording_dir`: Path to the recording directory containing `game_states.bin`
- `output_file`: Path to the output replay database file (typically with `.db` extension)

### Options

- `--mode MODE`: Patch creation mode - `state` (default) or `json`
- `--game-id ID`: Specify game ID explicitly (auto-detected if not provided)
- `--player-id ID`: Specify player ID explicitly (auto-detected if not provided)
- `--dump-json`: Dump game states and JSON responses to separate files instead of creating a replay
- `--json-output-dir DIR`: Directory for JSON output (default: `recording_dir/json_dumps`)
- `-v, --verbose`: Enable verbose logging (DEBUG level)
- `-q, --quiet`: Quiet mode (only ERROR level)

### Examples

Convert a recording to a replay file:
```bash
record-to-replay recordings/my_recording replay.db
```

Convert with verbose output:
```bash
record-to-replay recordings/my_recording replay.db -v
```

Specify game and player IDs explicitly:
```bash
record-to-replay recordings/my_recording replay.db --game-id 12345 --player-id 67890
```

Dump game states and JSON responses to separate files:
```bash
record-to-replay recordings/my_recording --dump-json
```


Dump with custom output directory:
```bash
record-to-replay recordings/my_recording --dump-json --json-output-dir my_json_output
```

## Input Format

The converter expects a recording directory with the following structure:

```
recording_dir/
├── game_states.bin      # Required: Binary file with compressed game states
├── static_map_data.bin  # Optional: Compressed static map data
├── responses.jsonl.zst  # Optional: Compressed JSON responses (not used by converter)
├── recording.log        # Optional: Session logs
└── metadata.json        # Optional: Recording metadata
```

### Game States File Format

The `game_states.bin` file contains:
- 8 bytes: timestamp in milliseconds (big-endian)
- 4 bytes: compressed data length (big-endian)
- N bytes: compressed game state (zstandard compressed pickle)

This pattern repeats for each game state update.

## Output Format

The converter creates a replay database (`.db` file) with:
- Initial game state snapshot
- Bidirectional patches between consecutive states
- Static map data (if available)
- Metadata (game ID, player ID, timestamps)

The output replay file can be used with:
- `replay-debug` tool for inspection and debugging
- Replay playback functionality in the interface
- Any other tools that work with replay files

## How It Works

1. **Read Game States**: The converter reads all compressed game states from the binary file
2. **Extract Metadata**: Game ID and player ID are extracted from the first state (unless provided explicitly)
3. **Create Initial State**: The first game state becomes the replay's initial snapshot
4. **Generate Patches**: For each pair of consecutive states, a bidirectional patch is created
5. **Write Replay**: All data is written to a SQLite database in the standard replay format

## Integration with Other Tools

### Recording Workflow
```bash
# Step 1: Record game session
recorder config.json

# Step 2: Convert to replay
record-to-replay recordings/recording_20231215_120000 replay.db

# Step 3: Inspect or debug
replay-debug replay.db
```

### Benefits of Conversion

- **Time Travel**: Navigate forward and backward through the game history
- **Efficient Storage**: Patches are more space-efficient than storing complete states
- **Debug Tools**: Use all replay debug commands on converted recordings
- **Analysis**: Easier to analyze specific game events and state changes

## Limitations

- The converter only processes `game_states.bin` and ignores JSON responses
- Conversion time is proportional to the number of game states in the recording
- Large recordings may take several minutes to convert
- The converter requires sufficient memory to hold game states during patch generation

## Troubleshooting

### File Not Found
```
Error: Recording directory not found: recordings/my_recording
```
Make sure the recording directory path is correct and the directory exists.

### Missing Game States File
```
Error: Game states file not found: recordings/my_recording/game_states.bin
```
The recording directory must contain a `game_states.bin` file. This file is created by the recorder tool.

### Cannot Determine Game ID
```
Error: Could not determine game_id from recording
```
Use the `--game-id` option to specify the game ID explicitly.

### Memory Issues
If you encounter out-of-memory errors with very large recordings, try:
- Converting on a machine with more RAM
- Breaking the recording into smaller segments
- Reducing the number of state updates in the recording

## Dumping Game States to JSON

The converter can also dump game states and JSON responses directly to JSON files for inspection, analysis, or external processing.

### Output Structure

When using `--dump-json`, the following structure is created:

```
json_dumps/
├── game_states/
│   ├── game_state_0000_1699999999000.json
│   ├── game_state_0001_1700000010000.json
│   └── ...
├── json_responses/
│   ├── response_0000_1699999999000.json
│   ├── response_0001_1700000010000.json
│   └── ...
└── static_map_data.json
```

Each game state file includes:
- `timestamp_ms`: Unix timestamp in milliseconds
- `timestamp_iso`: ISO 8601 formatted timestamp
- `state_index`: Sequential index of the state
- `game_state`: Full game state in JSON format

Each JSON response file includes:
- `timestamp_ms`: Unix timestamp in milliseconds
- `timestamp_iso`: ISO 8601 formatted timestamp
- `response_index`: Sequential index of the response
- `response`: Full JSON response from the server

### Using JSON Dumps

**Debugging and inspection:**
```bash
# Dump to separate files
record-to-replay recordings/my_recording --dump-json

# View a specific state
cat recordings/my_recording/json_dumps/game_states/game_state_0042_*.json | jq .

# View a specific response
cat recordings/my_recording/json_dumps/json_responses/response_0042_*.json | jq .
```

**Load into Python:**
```python
import json
from pathlib import Path

# Load a specific game state
with open("json_dumps/game_states/game_state_0000_1699999999000.json") as f:
    state_data = json.load(f)
    game_state = state_data["game_state"]

# Load a specific JSON response
with open("json_dumps/json_responses/response_0000_1699999999000.json") as f:
    response_data = json.load(f)
    response = response_data["response"]

# Process all states
json_dumps_dir = Path("json_dumps/game_states")
for state_file in sorted(json_dumps_dir.glob("game_state_*.json")):
    with open(state_file) as f:
        data = json.load(f)
        print(f"State {data['state_index']} at {data['timestamp_iso']}")
```

For more details, see [DUMP_JSON.md](./DUMP_JSON.md).

## Using as a Library

You can also use the converter programmatically:

```python
from tools.record_to_replay import RecordToReplayConverter

# Create converter
converter = RecordToReplayConverter("recordings/my_recording")

# Convert to replay
success = converter.convert(
    output_file="replay.db",
    game_id=12345,  # optional
    player_id=67890  # optional
)

if success:
    print("Conversion successful!")

# Or dump to JSON
success = converter.dump_to_json(
    output_dir="my_json_output"  # optional
)

if success:
    print("JSON dump successful!")
```

## See Also

- [JSON Dump Documentation](./DUMP_JSON.md) - Detailed guide for dumping to JSON
- [Recorder CLI Tool](../recorder/README.md) - For creating recordings
- [Replay Debug CLI Tool](../replay_debug/README.md) - For inspecting replay files
- [Replay System Documentation](../../docs/replay_system.md) - For replay format details
