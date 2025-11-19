"""
Interactive shell for the Replay Debug CLI Tool.
"""
import os
import shlex
import atexit

from .constants import *


def setup_readline():
    """Set up readline for command history."""
    try:
        import readline
        # Set up history file
        histfile = os.path.expanduser("~/.replay_debug_history")
        try:
            readline.read_history_file(histfile)
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
        # Save history on exit
        atexit.register(readline.write_history_file, histfile)
    except ImportError:
        # readline not available on this platform
        pass


def print_interactive_help():
    """Print help for interactive mode."""
    print("""
Available Commands:
  list-patches (lp)                           - List all patches with indices
  view-patch (vp) <index> [--limit N]         - View a patch by its index number
  view-patch (vp) <from_ts> <to_ts> [--limit N] - View a specific patch by timestamps
  view-operations-by-path (vop) <path> [opts] - View operations by path
    Options: --limit N, --direction forward|backward|both, --full-width
  operations-overview (oo) [--direction ...]  - Show operations overview
  count-operations (co)                       - Count all operations
  count-operations-by-path (cop) <path> [...] - Count operations by path
    Options: --direction forward|backward|both
  metadata (md)                               - Display replay metadata
  help (?)                                    - Show this help
  exit, quit, q                               - Exit the shell

Navigation:
  - Use UP/DOWN arrow keys to cycle through command history
  - After 'list-patches', use 'vp <index>' to quickly view a patch
  - In 'view-operations-by-path', the 'Idx' column shows patch index

Examples:
  list-patches
  vp 1                                         # View first patch from list
  vp 1 --limit 50                             # View first 50 operations of patch 1
  vop "states/map_state" --direction forward --full-width
  oo --direction forward
  cop "states/player_state"
  metadata                                     # Show replay metadata
        """)


def run_interactive_shell(cli):
    """Run an interactive shell for executing commands.
    
    Args:
        cli: ReplayDebugCLI instance
    """
    setup_readline()
    
    print(f"\nReplay Debug Shell - {cli.filename}")
    print("Type 'help' for available commands, 'exit' or 'quit' to exit\n")
    
    while True:
        try:
            # Get user input
            user_input = input(SHELL_PROMPT).strip()
            
            if not user_input:
                continue
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Exiting...")
                break
            
            # Check for help
            if user_input.lower() in ['help', '?']:
                print_interactive_help()
                continue
            
            # Parse the command
            try:
                args = shlex.split(user_input)
            except ValueError as e:
                print(f"Error parsing command: {e}")
                continue
            
            if not args:
                continue
            
            command = args[0]
            
            # Execute commands
            try:
                if command == "list-patches" or command == "lp":
                    cli.list_patches()
                
                elif command == "view-patch" or command == "vp":
                    if len(args) < 2:
                        print("Usage: view-patch <index> [--limit N] OR view-patch <from_timestamp> <to_timestamp> [--limit N]")
                        continue
                    
                    # Parse optional --limit argument
                    limit = None
                    if '--limit' in args:
                        idx = args.index('--limit')
                        if idx + 1 < len(args):
                            try:
                                limit = int(args[idx + 1])
                            except ValueError:
                                print("Error: --limit value must be an integer")
                                continue
                    
                    # Check if single argument (index) or two arguments (timestamps)
                    if len(args) == 2 or (len(args) > 2 and args[2].startswith('--')):
                        # Single argument - treat as index
                        try:
                            index = int(args[1])
                            cli.view_patch_by_index(index, limit)
                        except ValueError:
                            print("Error: Index must be an integer")
                    else:
                        # Two arguments - treat as timestamps
                        try:
                            from_ts = int(args[1])
                            to_ts = int(args[2])
                            cli.view_patch(from_ts, to_ts, limit)
                        except ValueError:
                            print("Error: Timestamps must be integers")
                
                elif command == "metadata" or command == "md":
                    cli.display_metadata()
                
                elif command == "view-operations-by-path" or command == "vop":
                    if len(args) < 2:
                        print("Usage: view-operations-by-path <path_prefix> [--limit N] [--direction forward|backward|both] [--full-width]")
                        continue
                    
                    path_prefix = args[1]
                    limit = DEFAULT_LIMIT
                    direction = DEFAULT_DIRECTION
                    full_width = False
                    
                    # Parse optional arguments
                    i = 2
                    while i < len(args):
                        if args[i] == '--limit' and i + 1 < len(args):
                            limit = int(args[i + 1])
                            i += 2
                        elif args[i] == '--direction' and i + 1 < len(args):
                            direction = args[i + 1]
                            i += 2
                        elif args[i] == '--full-width':
                            full_width = True
                            i += 1
                        else:
                            i += 1
                    
                    cli.view_operations_by_path(path_prefix, limit, direction, full_width)
                
                elif command == "operations-overview" or command == "oo":
                    direction = DEFAULT_DIRECTION
                    if '--direction' in args:
                        idx = args.index('--direction')
                        if idx + 1 < len(args):
                            direction = args[idx + 1]
                    
                    cli.operations_overview(direction)
                
                elif command == "count-operations" or command == "co":
                    cli.count_operations()
                
                elif command == "count-operations-by-path" or command == "cop":
                    if len(args) < 2:
                        print("Usage: count-operations-by-path <path_prefix> [--direction forward|backward|both]")
                        continue
                    
                    path_prefix = args[1]
                    direction = DEFAULT_DIRECTION
                    
                    if '--direction' in args:
                        idx = args.index('--direction')
                        if idx + 1 < len(args):
                            direction = args[idx + 1]
                    
                    cli.count_operations_by_path(path_prefix, direction)
                
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")
            
            except Exception as e:
                print(f"Error executing command: {e}")
                import traceback
                traceback.print_exc()
        
        except KeyboardInterrupt:
            print("\nUse 'exit' or 'quit' to exit")
            continue
        except EOFError:
            print("\nExiting...")
            break
