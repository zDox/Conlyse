# paths.py
from pathlib import Path

# Resolve project root no matter where this file is imported from
PROJECT_ROOT = Path(__file__).resolve().parent

TEST_DIR = PROJECT_ROOT / "tests"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
TOOLS_DIR = PROJECT_ROOT / "tools"
PERF_TEST_DIR = PROJECT_ROOT / "performance_tests"
CONFLICT_DIR = PROJECT_ROOT / "conflict_interface"

TEST_DATA = PROJECT_ROOT / "tests" / "test_data"