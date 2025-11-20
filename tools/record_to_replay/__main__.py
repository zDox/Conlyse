"""
CLI entry point for the record-to-replay converter tool.
"""
import argparse
import logging
import sys

from tools.record_to_replay.converter import RecordToReplayConverter
from conflict_interface.logger_config import setup_library_logger


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert recorder data to replay format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a recording to a replay file (default: state-based mode)
  record-to-replay recordings/my_recording replay.db
  
  # Convert using JSON-based mode
  record-to-replay recordings/my_recording replay.db --mode json
  
  # Dump game states and JSON requests/responses to separate files
  record-to-replay recordings/my_recording --dump-json
  
  # Convert with verbose output
  record-to-replay recordings/my_recording replay.db -v
  
  # Specify game and player IDs explicitly
  record-to-replay recordings/my_recording replay.db --game-id 12345 --player-id 67890

The recording directory should contain:
  - game_states.bin: Binary file with compressed game states
  - static_map_data.bin: (optional) Compressed static map data
  - requests.jsonl.zst: (optional) Compressed JSON request parameters
  - responses.jsonl.zst: (optional) Compressed JSON responses
  - metadata.json: (optional) Recording metadata

Patch creation modes:
  - state: Create patches from consecutive game states (default, faster)
  - json: Create patches by parsing JSON responses and applying updates
        """
    )
    
    parser.add_argument(
        'recording_dir',
        help='Path to the recording directory'
    )
    
    parser.add_argument(
        'output_file',
        nargs='?',
        help='Path to the output replay database file (.db) - not required with --dump-json'
    )

    parser.add_argument(
        '--dump-json',
        action='store_true',
        help='Dump game states and JSON responses to separate files instead of creating a replay'
    )

    parser.add_argument(
        '--json-output-dir',
        help='Directory for JSON output (default: recording_dir/json_dumps)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['state', 'json'],
        default='state',
        help='Patch creation mode: "state" (default) or "json"'
    )
    
    parser.add_argument(
        '--game-id',
        type=int,
        help='Game ID (auto-detected from recording if not provided)'
    )
    
    parser.add_argument(
        '--player-id',
        type=int,
        help='Player ID (auto-detected from recording if not provided)'
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
    
    # Validate arguments
    if not args.dump_json and not args.output_file:
        parser.error("output_file is required unless --dump-json is specified")

    # Setup logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    setup_library_logger(log_level)
    
    # Create converter
    try:
        converter = RecordToReplayConverter(args.recording_dir, patch_mode=args.mode)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Handle dump-json mode
    if args.dump_json:
        try:
            success = converter.dump_to_json(
                output_dir=args.json_output_dir
            )

            if success:
                output_dir = args.json_output_dir or f"{args.recording_dir}/json_dumps"
                print(f"Successfully dumped to JSON: {output_dir}")
                sys.exit(0)
            else:
                print("JSON dump failed. Check logs for details.")
                sys.exit(1)

        except KeyboardInterrupt:
            print("\nDump interrupted by user")
            sys.exit(130)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    # Convert to replay
    try:
        success = converter.convert(
            output_file=args.output_file,
            game_id=args.game_id,
            player_id=args.player_id
        )
        
        if success:
            print(f"Successfully converted recording to replay: {args.output_file}")
            sys.exit(0)
        else:
            print("Conversion failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
