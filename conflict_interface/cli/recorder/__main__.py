"""
CLI entry point for the recorder tool.
"""
import argparse
import json
import logging
import sys

from conflict_interface.cli.recorder.recorder import Recorder
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

For a complete list of action types and their parameters, see the documentation.
        """
    )
    
    parser.add_argument(
        'config',
        help='Path to the configuration JSON file'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (only ERROR level)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    setup_library_logger(log_level)
    
    # Load configuration
    config = load_config_file(args.config)
    
    # Create and run recorder
    recorder = Recorder(config)
    
    try:
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
