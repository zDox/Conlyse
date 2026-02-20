# ConflictInterface

A Python interface for [Conflict of Nations](https://www.conflictnations.com/), providing programmatic access to game state management, API interactions, and comprehensive replay functionality.

## Features

- 🎮 **Game State Management**: Complete game state representation with type-safe data structures
- 🔄 **Replay System**: Bidirectional replay recording and playback with efficient patch-based storage
- 🛠️ **CLI Tools**: Command-line utilities for recording, converting, and debugging replays
- 📡 **API Wrapper**: Pythonic interface to Conflict of Nations API endpoints
- 🔍 **Game Analysis**: Tools for analyzing game data, strategies, and state changes

## Installation

```bash
pip install -e .
```

### Optional Dependencies

Install additional features with extras:

```bash
# Documentation generation
pip install -e ".[docs]"

# All CLI tools
pip install -e ".[tools]"

# Testing utilities
pip install -e ".[tests]"

# Development dependencies
pip install -e ".[dev]"
```

## Docker Deployment 🐳

The complete stack (Server Observer, Redis, PostgreSQL, MinIO S3, Server Converter, **Conlyse API**) can be deployed with Docker:

```bash
# Quick start
cp .env.example .env
docker-compose up -d

# Check status
docker-compose ps

# Access MinIO console
open http://localhost:9001

# Access Conlyse API (Swagger UI)
open http://localhost:8000/docs
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete documentation.

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

### Recording Game Sessions

```bash
# Record a game session using the recorder CLI
recorder config.json

# Convert recording to replay format
recording-converter --recording-dir recordings/my_game --output-replay my_game.db

# Debug and analyze replay
replay-debug my_game.db
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

## CLI Tools

ConflictInterface includes several command-line tools for working with game data:

### recorder

Record game sessions with scripted actions.

```bash
recorder config.json -v
```

See [Recorder Documentation](tools/recorder/README.md) for details.

### recording-converter

Convert recordings to replay format or export to JSON.

```bash
recording-converter --recording-dir recordings/my_game --output-replay output.db
```

See [Recording Converter Documentation](tools/recording_converter/README.md) for details.

### server-converter

Process game responses from Redis streams and convert them to replay files. Works in conjunction with server-observer to automatically create and manage replays.

```bash
server-converter config.json
```

See [Server Converter Documentation](tools/server_converter/README.md) for details.

### replay-debug

Interactive debugging and analysis tool for replay files.

```bash
replay-debug replay.db
```

See [Replay Debug Documentation](tools/replay_debug/README.md) for details.

### Conlyse API

FastAPI service providing authentication, 2FA, device management, RBAC, and pre-signed download URLs.

```bash
# Run with Docker Compose (recommended)
docker-compose up -d api

# Interactive API docs
open http://localhost:8000/docs
```

See [API Documentation](tools/api/README.md) for full setup and endpoint reference.

## Documentation

- **[Replay System](docs/REPLAY_SYSTEM.md)**: Comprehensive documentation on the replay system architecture, algorithms, and usage
- **[API Documentation](https://conflict-interface.readthedocs.io/)**: Full API reference (ReadTheDocs)
- **Examples**: See the [examples/](examples/) directory for code samples

## Project Structure

```
ConflictInterface/
├── conflict_interface/      # Main package
│   ├── data_types/          # Game state data structures
│   ├── interface/           # Game and replay interfaces
│   ├── replay/              # Replay system implementation
│   ├── utils/               # Utility modules
│   ├── game_api.py          # Game server API wrapper
│   └── hub_api.py           # Hub API wrapper
├── tools/                   # Command-line tools & services
│   ├── api/                 # Conlyse API (FastAPI service)
│   ├── recorder/            # Game session recorder
│   ├── recording_converter/ # Recording format converter
│   └── replay_debug/        # Replay debugging tool
├── examples/                # Example scripts
├── tests/                   # Test suite
└── docs/                    # Documentation
```

## Examples

The [examples/](examples/) directory contains various usage examples:

- `game_join.py` - Join a game session
- `start_of_game.py` - Initialize a new game
- `record_replay.py` - Record game sessions
- `replay_roundtrip.py` - Replay system demonstration
- `build_upgrade.py` - Build structures
- `mobilize_unit.py` - Create military units
- `command_army.py` - Issue army commands
- `research.py` - Research technologies

## Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[tests]"

# Run tests
python -m pytest tests/
```

### Building Documentation

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build documentation
cd docs
make html
```

## License

Proprietary License - All Rights Reserved

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Authors

- zDox
- NikNam3

## Links

- **GitHub**: https://github.com/zDox/ConflictInterface
- **Documentation**: https://conflict-interface.readthedocs.io/
- **Game Website**: https://www.conflictnations.com/
