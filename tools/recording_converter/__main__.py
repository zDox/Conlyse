"""
CLI entry point for the record-to-replay converter tool.
"""
import argparse
import logging
import sys

from tools.recording_converter.converter import RecordingConverter
from tools.recording_converter.enums import OperatingMode
from tools.recording_converter.recorder_logger import setup_converter_logger


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
        '--recording-dir',
        help='Path to the recording directory'
    )
    
    parser.add_argument(
        '--output-replay',
        nargs='?',
        help='Path to the output replay database file - required unless in rtj mode'
    )

    parser.add_argument(
        '--output-dir',
        nargs='?',
        help='Path to the output dir for JSON files - required in rtj mode'
    )
    
    parser.add_argument(
        '--mode',
        choices=['gmr', 'rur', 'rtj'],
        default='gmr',
        help='Operation Mode: gmr (from_game_state_using_make_bipatch_to_replay), rur (from_json_responses_using_update_to_replay), rtj (from_recording_to_json)'
    )
    
    parser.add_argument(
        '--game-id',
        type=int,
        help='Game ID'
    )
    
    parser.add_argument(
        '--player-id',
        type=int,
        help='Player ID'
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
    
    setup_converter_logger(log_level)
    
    # Create converter
    try:
        op_mode = OperatingMode.gmr
        match args.mode:
            case 'gmr' :
                op_mode = OperatingMode.gmr
            case 'rur' :
                op_mode = OperatingMode.rur
            case 'rtj' :
                op_mode = OperatingMode.rtj

        converter = RecordingConverter(args.recording_dir, op_mode)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Convert
    try:
        success = False
        match op_mode:
            case OperatingMode.rtj:
                if not args.output_dir:
                    print("Error: Output directory is required in rtj mode")
                    sys.exit(1)
                success = converter.convert(
                    output=args.output_dir
                )

                if success:
                    print(f"Successfully converted recording to JSON files in: {args.output_dir}")
                    sys.exit(0)
                else:
                    print("Convertion failed. Check logs for details.")
                    sys.exit(1)
            case OperatingMode.gmr | OperatingMode.rur:
                success = converter.convert(
                    output=args.output_replay,
                    game_id=args.game_id,
                    player_id=args.player_id
                )
            case _:
                if not args.output_replay:
                    print("Error: Output replay file is required in gmr and rur modes")
                    sys.exit(1)
        
        if success:
            print(f"Successfully converted recording to replay: {args.output_replay}")
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
