"""
CLI entry point for the ServerObserver tool.
"""
import argparse
import json
import logging
import sys

from conflict_interface.logger_config import setup_library_logger
from tools.recorder.account_pool import AccountPool
from tools.server_observer.memory_profiler import MemoryProfiler
from tools.server_observer.memory_profiler import MonitoredServerObserver
from tools.server_observer.server_observer import ServerObserver


def load_config_file(config_path: str) -> dict:
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ServerObserver tool for recording server responses until game end.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("config", help="Path to the configuration JSON file")
    args = parser.parse_args()

    # Setup logging similar to recorder: console info for observer logger.
    setup_library_logger(logging.INFO)
    recording_logger = logging.getLogger("rec")
    recording_logger.setLevel(logging.DEBUG)
    recording_logger.propagate = False
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    recording_logger.addHandler(console_handler)

    config = load_config_file(args.config)

    account_pool = None
    account_pool_path = config.get("account_pool_path")
    if account_pool_path:
        account_pool = AccountPool(account_pool_path, webshare_token=config.get("WEBSHARE_API_TOKEN"))

    observer = ServerObserver(config, account_pool=account_pool)

    profiler = MonitoredServerObserver(observer)
    profiler.run()
    try:
        success = observer.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nObservation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
