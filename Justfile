default:
    @just --list

# Install all Python library, services, and tools in editable mode
install-all:
    pip install -e libs/conflict_interface
    pip install -e tools/recorder
    pip install -e tools/recording_converter
    pip install -e tools/replay_debug
    pip install -e tools/api

# Run tests
test-lib:
    pytest

test-api:
    cd tools/api && pytest

# Lint and format (repo-wide)
lint:
    ruff check .

format:
    black .

