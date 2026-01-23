"""
CLI entry point for the recorder tool.
"""
import argparse
import json
import logging
import sys

from tools.recorder.recorder import Recorder
from tools.recorder.multi_recorder import MultiRecorder
from tools.recorder.account_pool import AccountPool
from conflict_interface.logger_config import setup_library_logger


def load_config_file(config_path: str) -> dict:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Recorder CLI tool for recording Conflict of Nations game sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example configuration file:
{
  "username": "your_username",
  "password": "your_password",
  "scenario_id": 5975,
  "country_name": "USA",
  "output_dir": "./recordings",
  "recording_name": "my_game_session",
  "actions": [
    {
      "type": "build_upgrade",
      "city_name": "Washington",
      "building_name": "Arms Industry",
      "tier": 1
    },
    {
      "type": "sleep_with_updates",
      "duration": "5m",
      "update_interval": 30
    }
  ]
}

To use account pool for multi-account support, add:
{
  "account_pool_path": "path/to/account_pool.json",
  ...
}

For a complete list of action types and their parameters, see the documentation.
        """
    )
    
    parser.add_argument(
        'config',
        help='Path to the configuration JSON file'
    )

    parser.add_argument(
        '--save-game-states',
        action='store_true',
        help='Enable saving of each game state during recording'
    )
    
    args = parser.parse_args()
    
    # Setup logging Recoding to console and Library turned off
    # ----------------------------
    # Create loggers first
    # ----------------------------
    library_logger = logging.getLogger("con_itf")
    library_logger.setLevel(logging.DEBUG)
    library_logger.propagate = False  # prevent console output by default

    recording_logger = logging.getLogger("rec")
    recording_logger.setLevel(logging.DEBUG)
    recording_logger.propagate = False

    # Optional: add a console handler to recording logger now
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    recording_logger.addHandler(console_handler)


    # Load configuration
    config = load_config_file(args.config)
    
    # Load account pool if specified in config
    account_pool = None
    account_pool_path = config.get('account_pool_path')
    if account_pool_path:
        account_pool = AccountPool(account_pool_path)
    
    # Create and run recorder
    try:
        if isinstance(config.get("scenario_ids"), list) and len(config.get("scenario_ids") or []) > 0:
            recorder = MultiRecorder(config, account_pool=account_pool)
        else:
            recorder = Recorder(config, account_pool=account_pool, save_game_states=args.save_game_states)

        success = recorder.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nRecording interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
