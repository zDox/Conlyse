"""
Main entry point for the Replay Debug CLI Tool.
"""
import argparse
import sys

from .cli import ReplayDebugCLI
from .shell import run_interactive_shell
from .constants import DEFAULT_LIMIT, DEFAULT_DIRECTION


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Replay Debug CLI Tool - Inspect and debug replay files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interactive Mode:
  # Start interactive shell (recommended)
  %(prog)s replay.db
  
  # Then run commands without repeating the replay path:
  replay-debug> list-patches
  replay-debug> vop "states/map_state" --direction forward --full-width
  replay-debug> exit

Single Command Mode:
  # Run a single command and exit
  %(prog)s replay.db list-patches
  %(prog)s replay.db view-operations-by-path "states/map_state" --direction forward
  %(prog)s replay.db operations-overview
        """
    )
    
    parser.add_argument(
        "replay_file",
        help="Path to the replay database file (.db)"
    )
    
    parser.add_argument(
        "command",
        nargs='?',
        help="Command to execute. If omitted, starts interactive shell."
    )
    
    # Add --full-width flag for better output
    parser.add_argument(
        "--full-width",
        action="store_true",
        help="Don't truncate paths and values in output"
    )
    
    # Parse known args to handle both interactive and command modes
    args, remaining = parser.parse_known_args()
    
    # Check if replay file is provided
    if not args.replay_file:
        parser.print_help()
        print("\nError: replay_file is required")
        return 1
    
    # Create CLI instance
    cli = ReplayDebugCLI(args.replay_file)
    
    # Open the replay
    if not cli.open_replay():
        return 1
    
    try:
        # If no command provided, start interactive shell
        if not args.command:
            run_interactive_shell(cli)
            return 0
        
        # Otherwise, execute the single command
        command = args.command
        cmd_args = remaining
        
        # Execute commands based on command name
        if command == "list-patches":
            cli.list_patches()
        
        elif command == "view-patch":
            if len(cmd_args) < 2:
                print("Usage: view-patch <from_timestamp> <to_timestamp>")
                return 1
            try:
                from_ts = int(cmd_args[0])
                to_ts = int(cmd_args[1])
                cli.view_patch(from_ts, to_ts)
            except ValueError:
                print("Error: Timestamps must be integers")
                return 1
        
        elif command == "view-operations-by-path":
            if len(cmd_args) < 1:
                print("Usage: view-operations-by-path <path_prefix> [--limit N] [--direction forward|backward|both] [--full-width]")
                return 1
            
            path_prefix = cmd_args[0]
            limit = DEFAULT_LIMIT
            direction = DEFAULT_DIRECTION
            full_width = args.full_width
            
            # Parse optional arguments
            i = 1
            while i < len(cmd_args):
                if cmd_args[i] == '--limit' and i + 1 < len(cmd_args):
                    limit = int(cmd_args[i + 1])
                    i += 2
                elif cmd_args[i] == '--direction' and i + 1 < len(cmd_args):
                    direction = cmd_args[i + 1]
                    i += 2
                elif cmd_args[i] == '--full-width':
                    full_width = True
                    i += 1
                else:
                    i += 1
            
            cli.view_operations_by_path(path_prefix, limit, direction, full_width)
        
        elif command == "operations-overview":
            direction = DEFAULT_DIRECTION
            if '--direction' in cmd_args:
                idx = cmd_args.index('--direction')
                if idx + 1 < len(cmd_args):
                    direction = cmd_args[idx + 1]
            
            cli.operations_overview(direction)
        
        elif command == "count-operations":
            cli.count_operations()
        
        elif command == "count-operations-by-path":
            if len(cmd_args) < 1:
                print("Usage: count-operations-by-path <path_prefix> [--direction forward|backward|both]")
                return 1
            
            path_prefix = cmd_args[0]
            direction = DEFAULT_DIRECTION
            
            if '--direction' in cmd_args:
                idx = cmd_args.index('--direction')
                if idx + 1 < len(cmd_args):
                    direction = cmd_args[idx + 1]
            
            cli.count_operations_by_path(path_prefix, direction)
        
        else:
            print(f"Unknown command: {command}")
            print("Available commands: list-patches, view-patch, view-operations-by-path, operations-overview, count-operations, count-operations-by-path")
            return 1
    
    finally:
        cli.close_replay()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
