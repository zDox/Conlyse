# paths.py
from pathlib import Path

# Resolve project root no matter where this file is imported from
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFLICT_DIR = PROJECT_ROOT/"libs" / "conflict_interface"

TEST_DIR = CONFLICT_DIR / "tests"
EXAMPLES_DIR = CONFLICT_DIR / "examples"
TOOLS_DIR = CONFLICT_DIR / "tools"
PERF_TEST_DIR = CONFLICT_DIR / "performance_tests"

TEST_DATA = CONFLICT_DIR / "tests" / "test_data"