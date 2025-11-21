# Recording Converter CLI Tool

A command-line tool for converting recorder data to a different format in Conflict Interface.

## Overview

The Recording Converter transforms recording data (created by the `recorder` tool) into replay files or JSON dumps. This allows you to:
- Convert compressed game state recordings into replay databases
- Use the replay debug tools on converted recordings
- Export recordings to JSON format for external analysis

## Installation

The converter is installed automatically when you install the conflict-interface package:

```bash
pip install -e .
```

This will create a `recording-converter` command-line tool.

## Usage

### Basic Usage

Convert to replay database:
```bash
recording-converter --recording-dir <recording_dir> --output-replay <output_file>
```

Dump to JSON files:
```bash
recording-converter --recording-dir <recording_dir> --mode rtj --output-dir <output_dir>
```

### Arguments

- `--recording-dir`: Path to the recording directory containing recording files
- `--output-replay`: Path to the output replay database file (typically with `.db` extension)
- `--output-dir`: Path to the output directory for JSON files (used with `--mode rtj`)

### Options

- `--mode MODE`: Operating mode - `gmr` (default), `rur`, or `rtj`
  - `gmr`: from_game_state_using_make_bipatch_to_replay (faster, default)
  - `rur`: from_json_responses_using_update_to_replay
  - `rtj`: from_recording_to_json (dumps to JSON files)
- `--game-id ID`: Specify game ID explicitly (auto-detected if not provided)
- `--player-id ID`: Specify player ID explicitly (auto-detected if not provided)
- `-v, --verbose`: Enable verbose logging (DEBUG level)
- `-q, --quiet`: Quiet mode (only ERROR level)

### Examples

Convert a recording to a replay file (default mode):
```bash
recording-converter --recording-dir recordings/my_recording --output-replay replay.db
```

Convert using JSON-based replay mode:
```bash
recording-converter --recording-dir recordings/my_recording --output-replay replay.db --mode rur
```

Convert with verbose output:
```bash
recording-converter --recording-dir recordings/my_recording --output-replay replay.db -v
```

Specify game and player IDs explicitly:
```bash
recording-converter --recording-dir recordings/my_recording --output-replay replay.db --game-id 12345 --player-id 67890
```

Dump game states and JSON requests/responses to separate files:
```bash
recording-converter --recording-dir recordings/my_recording --mode rtj --output-dir json_output
```

Dump to default location (recording_dir/json_dumps):
```bash
recording-converter --recording-dir recordings/my_recording --mode rtj
```

## Input Format

The converter expects a recording directory with the following structure:

```
recording_dir/
├── game_states.bin      # Binary file with compressed game states (required for gmr/rur modes)
├── requests.jsonl.zst   # Compressed JSON request parameters (required for rur mode)
├── responses.jsonl.zst  # Compressed JSON responses (optional)
├── static_map_data.bin  # Compressed static map data (optional)
├── recording.log        # Session logs (optional)
└── metadata.json        # Recording metadata (optional)
```

### File Formats

**game_states.bin**:
- 8 bytes: timestamp in milliseconds (big-endian)
- 4 bytes: compressed data length (big-endian)
- N bytes: compressed game state (zstandard compressed pickle)

This pattern repeats for each game state update.

**requests.jsonl.zst / responses.jsonl.zst**:
- Zstandard-compressed JSONL files
- Each line contains a JSON object with timestamp and request/response data

## Output Format

The converter creates different outputs based on the operating mode:

### gmr/rur modes (Replay Database)
A replay database (`.db` file) with:
- Initial game state snapshot
- Bidirectional patches between consecutive states
- Static map data (if available)
- Metadata (game ID, player ID, timestamps)

The output replay file can be used with:
- `replay-debug` tool for inspection and debugging
- Replay playback functionality in the interface
- Any other tools that work with replay files

### rtj mode (JSON Dumps)
A directory containing:
```
output_dir/
├── game_states/
│   ├── game_state_0000_<timestamp>.json
│   ├── game_state_0001_<timestamp>.json
│   └── ...
├── json_requests/
│   ├── request_0000_<timestamp>.json
│   ├── request_0001_<timestamp>.json
│   └── ...
└── json_responses/
    ├── response_0000_<timestamp>.json
    ├── response_0001_<timestamp>.json
    └── ...
```

## How It Works

The converter supports three operating modes:

### Mode gmr (from_game_state_using_make_bipatch_to_replay)
**Default and fastest mode**
1. **Read Game States**: Reads all compressed game states from the binary file
2. **Extract Metadata**: Game ID and player ID are extracted from the first state
3. **Create Initial State**: The first game state becomes the replay's initial snapshot
4. **Generate Patches**: For each pair of consecutive states, a bidirectional patch is created using `make_bireplay_patch`
5. **Write Replay**: All data is written to a SQLite database in the standard replay format

### Mode rur (from_json_responses_using_update_to_replay)
**JSON-based mode**
1. **Read Initial State**: Reads the first game state as the initial snapshot
2. **Process JSON Requests**: Parses JSON request parameters to reconstruct actions
3. **Apply Updates**: Uses the game state `update()` function to apply each action
4. **Generate Patches**: Creates bidirectional patches from the state transitions
5. **Write Replay**: All data is written to a SQLite database

### Mode rtj (from_recording_to_json)
**JSON dump mode**
1. **Read Recording Files**: Reads game states, requests, and responses from the recording
2. **Convert to JSON**: Each item is converted to a JSON file with metadata
3. **Write Files**: Separate JSON files are created for each state, request, and response

## Integration with Other Tools

### Recording Workflow
```bash
# Step 1: Record game session
recorder config.json

# Step 2: Convert to replay
recording-converter --recording-dir recordings/recording_20231215_120000 --output-replay replay.db

# Step 3: Inspect or debug
replay-debug replay.db
```

### Benefits of Conversion

- **Time Travel**: Navigate forward and backward through the game history
- **Efficient Storage**: Patches are more space-efficient than storing complete states
- **Debug Tools**: Use all replay debug commands on converted recordings
- **Analysis**: Easier to analyze specific game events and state changes

## Limitations

- The `gmr` mode only processes `game_states.bin`
- The `rur` mode requires both `game_states.bin` and `requests.jsonl.zst`
- The `rtj` mode converts all available data (game states, requests, responses)
- Conversion time is proportional to the number of game states in the recording
- Large recordings may take several minutes to convert
- The converter requires sufficient memory to hold game states during patch generation

## Troubleshooting

### Recording Directory Not Found
```
Error: Recording directory not found: recordings/my_recording
```
Make sure the recording directory path is correct and the directory exists.

### Missing Game States File
```
Error: Game states file not found: recordings/my_recording/game_states.bin
```
The recording directory must contain a `game_states.bin` file. This file is created by the recorder tool. Required for `gmr` and `rur` modes.

### Missing Requests File
```
Error: Requests file not found: recordings/my_recording/requests.jsonl.zst
```
The `rur` mode requires a `requests.jsonl.zst` file. Use `gmr` mode instead, or ensure the recorder was configured to save requests.

### Output File Required
```
Error: Output replay file is required in gmr and rur modes
```
Specify the output replay file with `--output-replay replay.db`.

### Output Directory Required
```
Error: Output directory is required in rtj mode
```
Specify the output directory with `--output-dir json_output` when using `--mode rtj`.

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

The converter can also dump game states, JSON requests, and JSON responses directly to JSON files for inspection, analysis, or external processing using the `rtj` mode.

### Output Structure

When using `--mode rtj`, the following structure is created:

```
output_dir/
├── game_states/
│   ├── game_state_0000_1699999999000.json
│   ├── game_state_0001_1700000010000.json
│   └── ...
├── json_requests/
│   ├── request_0000_1699999999000.json
│   ├── request_0001_1700000010000.json
│   └── ...
└── json_responses/
    ├── response_0000_1699999999000.json
    ├── response_0001_1700000010000.json
    └── ...
```

Each game state file includes:
- `timestamp_ms`: Unix timestamp in milliseconds
- `timestamp_iso`: ISO 8601 formatted timestamp
- `state_index`: Sequential index of the state
- `game_state`: Full game state in JSON format

Each JSON request file includes:
- `timestamp_ms`: Unix timestamp in milliseconds
- `timestamp_iso`: ISO 8601 formatted timestamp
- `request_index`: Sequential index of the request
- `request`: Full JSON request parameters

Each JSON response file includes:
- `timestamp_ms`: Unix timestamp in milliseconds
- `timestamp_iso`: ISO 8601 formatted timestamp
- `response_index`: Sequential index of the response
- `response`: Full JSON response from the server

### Using JSON Dumps

**Debugging and inspection:**
```bash
# Dump to separate files
recording-converter --recording-dir recordings/my_recording --mode rtj --output-dir json_output

# View a specific state
cat json_output/game_states/game_state_0042_*.json | jq .

# View a specific request
cat json_output/json_requests/request_0042_*.json | jq .

# View a specific response
cat json_output/json_responses/response_0042_*.json | jq .
```

**Load into Python:**
```python
import json
from pathlib import Path

# Load a specific game state
with open("json_output/game_states/game_state_0000_1699999999000.json") as f:
    state_data = json.load(f)
    game_state = state_data["game_state"]

# Load a specific JSON request
with open("json_output/json_requests/request_0000_1699999999000.json") as f:
    request_data = json.load(f)
    request = request_data["request"]

# Load a specific JSON response
with open("json_output/json_responses/response_0000_1699999999000.json") as f:
    response_data = json.load(f)
    response = response_data["response"]

# Process all states
json_output_dir = Path("json_output/game_states")
for state_file in sorted(json_output_dir.glob("game_state_*.json")):
    with open(state_file) as f:
        data = json.load(f)
        print(f"State {data['state_index']} at {data['timestamp_iso']}")
```

For more details on the JSON dump format and usage, consult the code in `from_recording_to_json.py`.

## Using as a Library

You can also use the converter programmatically:

```python
from tools.recording_converter.converter import RecordingConverter
from tools.recording_converter.enums import OperatingMode

# Create converter for replay conversion (gmr mode)
converter = RecordingConverter(
    "recordings/my_recording",
    OperatingMode.gmr
)

# Convert to replay
success = converter.convert(
    output="replay.db",
    game_id=12345,  # optional
    player_id=67890  # optional
)

if success:
    print("Conversion successful!")

# Or dump to JSON (rtj mode)
converter_rtj = RecordingConverter(
    "recordings/my_recording",
    OperatingMode.rtj
)

success = converter_rtj.convert(
    output="my_json_output"  # optional, defaults to recording_dir/json_dumps
)

if success:
    print("JSON dump successful!")
```

## See Also

- [Recorder CLI Tool](../recorder/README.md) - For creating recordings
- [Replay Debug CLI Tool](../replay_debug/README.md) - For inspecting replay files
