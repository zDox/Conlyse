# Recorder CLI Tool

The Recorder CLI tool allows you to script and record game sessions in Conflict of Nations. It operates independently of the replay system and captures both compressed game states and server responses.

## Features

- **Independent Recording**: Does not use the record_replay function
- **Compressed Storage**: Stores game states and JSON responses in compressed format (zstandard)
- **Scriptable Actions**: Execute a sequence of predefined actions
- **Periodic Updates**: Option to update game state during wait periods
- **Multiple Action Types**: Build, mobilize, research, army commands, and more

## Installation

The recorder is installed automatically when you install the conflict-interface package:

```bash
pip install -e .
```

This will create a `recorder` command-line tool.

## Usage

### Basic Usage

```bash
recorder path/to/config.json
```

### Options

- `-v, --verbose`: Enable verbose logging (DEBUG level)
- `-q, --quiet`: Quiet mode (only ERROR level)

### Example

```bash
recorder examples/recorder_config_sample.json -v
```

## Configuration File

The recorder uses a JSON configuration file with the following structure:

### Authentication
- `username`: Your Conflict of Nations username
- `password`: Your password

### Game Selection
- `scenario_id`: The scenario ID to join
- `country_name`: (Optional) Specific country to play as

### Output Settings
- `output_dir`: Directory to save recordings (default: "./recordings")
- `recording_name`: (Optional) Name for this recording session

### Proxy Settings
- `proxy_url`: (Optional) Proxy URL for connections

### Actions

The `actions` array contains a list of actions to execute in sequence. Each action is a dictionary with a `type` field and additional parameters.

## Action Types

### Build Upgrade
Build a building in a city.

```json
{
  "type": "build_upgrade",
  "city_name": "Washington",
  "building_name": "Arms Industry",
  "tier": 1
}
```

### Cancel Upgrade
Cancel ongoing construction in a city.

```json
{
  "type": "cancel_upgrade",
  "city_name": "Washington"
}
```

### Mobilize Unit
Mobilize a unit in a city.

```json
{
  "type": "mobilize_unit",
  "city_name": "New York",
  "unit_name": "Infantry",
  "tier": 1
}
```

### Cancel Mobilization
Cancel ongoing mobilization in a city.

```json
{
  "type": "cancel_mobilization",
  "city_name": "New York"
}
```

### Research
Start research on a technology.

```json
{
  "type": "research",
  "research_name": "UAV",
  "tier": 1
}
```

### Cancel Research
Cancel ongoing research.

```json
{
  "type": "cancel_research"
}
```

### Sleep
Wait for a specified duration without updating the game state.

```json
{
  "type": "sleep",
  "duration": 10,
  "unit": "minutes"
}
```

Units can be `"seconds"` or `"minutes"`.

### Sleep with Updates
Wait for a specified duration while periodically updating the game state.

```json
{
  "type": "sleep_with_updates",
  "duration": 5,
  "unit": "minutes",
  "update_interval": 30
}
```

- `update_interval`: Seconds between updates (default: 10)

### Army Actions

Army actions can reference armies by either `army_id` or `army_number`.

#### Army Move
Move an army to a province center.

```json
{
  "type": "army_move",
  "army_number": 1,
  "province_name": "Boston"
}
```

#### Army Patrol
Send an aircraft to patrol over a province center.

```json
{
  "type": "army_patrol",
  "army_number": 2,
  "province_name": "New York"
}
```

#### Army Attack
Attack a province center.

```json
{
  "type": "army_attack",
  "army_number": 1,
  "province_name": "Toronto"
}
```

#### Army Cancel Commands
Cancel all commands for an army.

```json
{
  "type": "army_cancel_commands",
  "army_number": 1
}
```

## Output Format

The recorder creates a directory structure with the following files:

```
recordings/
└── recording_name/
    ├── game_states.bin      # Compressed game states
    ├── responses.jsonl.zst  # Compressed JSON responses
    ├── recording.log        # Session logs
    └── metadata.json        # Recording metadata
```

### Game States File (`game_states.bin`)
Binary file containing compressed game states. Each entry has:
- 8 bytes: timestamp (big-endian)
- 4 bytes: compressed data length (big-endian)
- N bytes: compressed game state (zstandard compressed pickle)

### Responses File (`responses.jsonl.zst`)
Compressed JSON responses from the game server. Each entry has:
- 8 bytes: timestamp (big-endian)
- 4 bytes: compressed data length (big-endian)
- N bytes: compressed JSON response (zstandard compressed)

### Log File (`recording.log`)
Text file containing all logs from the recording session with timestamps, including:
- Authentication and connection logs
- Action execution logs
- Game state update logs
- Error and warning messages

### Metadata File (`metadata.json`)
JSON file containing:
- Recording version
- Creation timestamp
- List of update timestamps

## Using as a Library

You can also use the recorder programmatically:

```python
from conflict_interface.cli.recorder import Recorder

config = {
    "username": "your_username",
    "password": "your_password",
    "scenario_id": 5975,
    "actions": [
        {
            "type": "build_upgrade",
            "city_name": "Washington",
            "building_name": "Arms Industry",
            "tier": 1
        }
    ]
}

recorder = Recorder(config)
success = recorder.run()
```

## Example Configuration

See `examples/recorder_config_sample.json` for a complete example configuration file.

## Notes

- The recorder operates **independently** of the replay system
- Each update saves both the game state and the server response
- All data is compressed using zstandard for efficient storage
- The recorder does not interfere with normal game replay functionality
- Army commands work for both airborne (patrol) and ground units
- Sleep actions can be used to wait for constructions/mobilizations to complete
