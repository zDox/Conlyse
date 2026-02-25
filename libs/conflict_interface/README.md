# conflict-interface

A Python library providing programmatic access to [Conflict of Nations](https://www.conflictnations.com/) game state management, API interactions, and comprehensive replay functionality.

## Overview

`conflict-interface` is the core Python library for interacting with Conflict of Nations. It provides:

- **Game State Management**: Complete game state representation with type-safe data structures
- **Replay System**: Bidirectional replay recording and playback with efficient patch-based storage
- **API Wrapper**: Pythonic interface to Conflict of Nations API endpoints
- **Game Analysis**: Tools for analyzing game data, strategies, and state changes

## Installation

### From Source

From the repository root:

```bash
pip install -e libs/conflict_interface
```

Or from within the library directory:

```bash
cd libs/conflict_interface
pip install -e .
```

### Optional Dependencies

Install additional features with extras:

```bash
# Documentation generation
pip install -e "libs/conflict_interface[docs]"

# Development helpers (includes pybind11 for building C++ extensions)
pip install -e "libs/conflict_interface[dev]"

# Long-patch test utilities
pip install -e "libs/conflict_interface[test-long-patches]"
```

## Quick Start

### Basic Game Interaction

```python
from conflict_interface.interface.game_interface import GameInterface

# Initialize and connect to a game
interface = GameInterface(username="your_username", password="your_password")
interface.login()
interface.join_game(game_id=12345)

# Access game state
game_state = interface.game_state
print(f"Current game day: {game_state.game_info.in_game_day}")

# Perform actions
interface.build_upgrade(city_name="Berlin", building_name="Arms Industry", tier=1)
interface.mobilize_unit(city_name="Berlin", unit_name="Infantry", tier=1)
```

### Working with Replays

```python
from conflict_interface.interface.replay_interface import ReplayInterface
from pathlib import Path
from datetime import datetime, timezone

# Load a replay file
replay = ReplayInterface(Path("my_game.db"))
replay.open()

# Navigate through time
timestamps = replay.get_timestamps()
replay.jump_to(timestamps[50])

# Access game state at any point in time
armies = replay.get_armies()
provinces = replay.game_state.states.map_state.provinces

replay.close()
```

## Package Structure

```
conflict_interface/
├── api/                    # API wrappers (game_api, hub_api)
├── data_types/             # Game state data structures
│   └── newest/            # Latest game state format
│       ├── map_state/     # Map and province data
│       ├── player_state/  # Player and team information
│       ├── army_state/    # Army and unit data
│       └── ...            # Other state modules
├── interface/              # Main interfaces
│   ├── game_interface.py  # Live game interaction
│   ├── replay_interface.py # Replay playback
│   └── hub_interface.py    # Hub API interaction
├── replay/                 # Replay system
│   ├── replay_builder.py  # Building replay files
│   ├── replay_patch.py    # Patch generation
│   └── ...                # Replay utilities
├── utils/                  # Utility modules
└── game_object/            # Game object parsing
```

## Key Features

### Game State Management

The library provides comprehensive type-safe data structures for all game state:

```python
from conflict_interface.interface.game_interface import GameInterface

interface = GameInterface(username="user", password="pass")
interface.login()
interface.join_game(game_id=12345)

# Access typed game state
game_state = interface.game_state
map_state = game_state.states.map_state
player_state = game_state.states.player_state

# Type-safe access to provinces, players, armies, etc.
province = map_state.provinces[0]
player = player_state.players[0]
```

### Replay System

Efficient bidirectional replay system with patch-based storage:

```python
from conflict_interface.interface.replay_interface import ReplayInterface
from pathlib import Path

replay = ReplayInterface(Path("replay.db"))
replay.open()

# Navigate through time
replay.jump_to_next_patch()  # Forward
replay.jump_to_previous_patch()  # Backward
replay.jump_to(timestamp)  # Specific time

# Access state at any point
current_state = replay.game_state
```

### API Wrappers

Pythonic wrappers for Conflict of Nations APIs:

```python
from conflict_interface.api.game_api import GameAPI

api = GameAPI()
response = api.make_game_server_request(
    action="updateProvinceConstruction",
    game_id=12345,
    player_id=67890,
    province_id=100,
    upgrade_id=5
)
```

## Examples

See the `examples/` directory for comprehensive usage examples:

- `game_join.py` - Join a game session
- `start_of_game.py` - Initialize a new game
- `record_replay.py` - Record game sessions
- `replay_roundtrip.py` - Replay system demonstration
- `build_upgrade.py` - Build structures
- `mobilize_unit.py` - Create military units
- `command_army.py` - Issue army commands
- `research.py` - Research technologies

## Development

### Building from Source

The library includes C++ extensions that need to be compiled:

```bash
cd libs/conflict_interface
pip install -e ".[dev]"  # Installs pybind11
pip install -e .         # Builds C++ extensions
```

### Running Tests

```bash
cd libs/conflict_interface
python tests/run_tests.py
```

### Building Documentation

```bash
pip install -e ".[docs]"
cd docs
make html
```

## Dependencies

Core dependencies:
- `requests` - HTTP client
- `numpy` - Numerical operations
- `shapely` - Geometric operations
- `msgpack`, `zstandard`, `lz4` - Compression
- `msgspec` - Fast serialization
- `pybind11` - C++ bindings

See `pyproject.toml` for the complete list.

## License

Proprietary License - All Rights Reserved

## Authors

- zDox
- NikNam3

## Links

- **GitHub**: https://github.com/zDox/ConflictInterface
- **Documentation**: https://conflict-interface.readthedocs.io/
- **Game Website**: https://www.conflictnations.com/
