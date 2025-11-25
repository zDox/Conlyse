"""
Interactive shell for the Replay Debug CLI Tool.

This module provides a unified interactive shell that supports all features:
navigation, state viewing, and patch analysis.
"""
import os
import atexit

from .constants import *
from .cli import ReplayDebugCLI
from .args_parser import CommandParser, resolve_alias


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


def print_help():
    """Print help for interactive mode."""
    print("""
Available Commands:

Navigation:
  info                                        - Display current replay position
  jump-relative (jr) <seconds>                - Jump by relative time
  jump-absolute (ja) <timestamp>              - Jump to absolute time (ISO format)
  jump-patches (jp) <num>                     - Jump by number of patches
  jump-index (ji) <index>                     - Jump to timestamp by index
  list-timestamps (lt) [--limit N] [--relative] - List all timestamps with indices

State Viewing:
  view-state (vs) <path> [--depth N]          - View game state at path
  list-states (ls)                            - List available state categories
  search-paths (sp) <term>                    - Search for paths containing term

Patch Analysis:
  list-patches (lp)                           - List all patches with indices
  view-patch (vp) <index> [--limit N]         - View a patch by its index number
  view-operations-by-path (vop) <path> [opts] - View operations by path
    Options: --limit N, --direction forward|backward|both, --full-width
  operations-overview (oo) [--direction ...]  - Show operations overview
  count-operations (co)                       - Count all operations
  count-operations-by-path (cop) <path> [...] - Count operations by path
    Options: --direction forward|backward|both
  metadata (md)                               - Display replay metadata

Advanced:
  ritf                                        - Show ReplayInterface info
  python                                      - Enter Python REPL with ritf
  help (?)                                    - Show this help
  exit, quit, q                               - Exit the shell

Examples:
  jr 60                       # Jump forward 60 seconds
  vs states/player_state      # View player state
  lp                          # List all patches
  vp 1 --limit 50            # View first 50 operations of patch 1
  python                      # Enter Python REPL
        """)


def run_interactive_shell(cli: ReplayDebugCLI):
    """Run an interactive shell for executing commands.
    
    Args:
        cli: ReplayDebugCLI instance
    """
    setup_readline()
    
    parser = CommandParser()
    
    print(f"\nReplay Debug Shell - {cli.filename}")
    print("Type 'help' for available commands, 'exit' or 'quit' to exit\n")
    
    # Make ritf available for advanced usage
    ritf = cli.get_ritf()
    
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
                print_help()
                continue
            
            # Parse the command
            try:
                command, positional, options = parser.parse_command(user_input)
            except ValueError as e:
                print(str(e))
                continue
            
            if not command:
                continue
            
            # Resolve alias
            command = resolve_alias(command)
            
            # Execute commands
            try:
                # Navigation commands
                if command == "info":
                    cli.display_info()
                
                elif command == "jump-relative":
                    if len(positional) < 1:
                        print("Usage: jump-relative <seconds>")
                        continue
                    try:
                        seconds = float(positional[0])
                        cli.jump_relative(seconds)
                    except ValueError:
                        print("Error: seconds must be a number")
                
                elif command == "jump-absolute":
                    if len(positional) < 1:
                        print("Usage: jump-absolute <timestamp>")
                        continue
                    cli.jump_absolute(positional[0])
                
                elif command == "jump-patches":
                    if len(positional) < 1:
                        print("Usage: jump-patches <num>")
                        continue
                    try:
                        num = int(positional[0])
                        cli.jump_patches(num)
                    except ValueError:
                        print("Error: num must be an integer")
                
                elif command == "jump-index":
                    if len(positional) < 1:
                        print("Usage: jump-index <index>")
                        continue
                    try:
                        index = int(positional[0])
                        cli.jump_index(index)
                    except ValueError:
                        print("Error: index must be an integer")
                
                elif command == "list-timestamps":
                    limit = parser.get_int_option(options, 'limit', 50)
                    relative = parser.get_bool_option(options, 'relative', False)
                    cli.list_timestamps(limit, relative)
                
                # State viewing commands
                elif command == "view-state":
                    if len(positional) < 1:
                        print("Usage: view-state <path> [--depth N]")
                        continue
                    path = positional[0]
                    max_depth = parser.get_int_option(options, 'depth', 5)
                    cli.view_game_object_path(path, max_depth)
                
                elif command == "list-states":
                    cli.list_states()
                
                elif command == "search-paths":
                    if len(positional) < 1:
                        print("Usage: search-paths <term>")
                        continue
                    cli.search_paths(positional[0])
                
                # Patch analysis commands
                elif command == "list-patches":
                    cli.list_patches()
                
                elif command == "view-patch":
                    if len(positional) < 1:
                        print("Usage: view-patch <index> [--limit N] OR view-patch <from_timestamp> <to_timestamp> [--limit N]")
                        continue
                    
                    limit = parser.get_int_option(options, 'limit', None)
                    
                    # Check if single argument (index) or two arguments (timestamps)
                    if len(positional) == 1:
                        # Single argument - treat as index
                        try:
                            index = int(positional[0])
                            cli.view_patch_by_index(index, limit)
                        except ValueError:
                            print("Error: Index must be an integer")
                    else:
                        # Two arguments - treat as timestamps
                        try:
                            from_ts = int(positional[0])
                            to_ts = int(positional[1])
                            cli.view_patch(from_ts, to_ts, limit)
                        except ValueError:
                            print("Error: Timestamps must be integers")
                
                elif command == "metadata":
                    cli.display_info()  # Using display_info instead of display_metadata
                
                elif command == "view-operations-by-path":
                    if len(positional) < 1:
                        print("Usage: view-operations-by-path <path_prefix> [--limit N] [--direction forward|backward|both] [--full-width]")
                        continue
                    
                    path_prefix = positional[0]
                    limit = parser.get_int_option(options, 'limit', DEFAULT_LIMIT)
                    direction = parser.get_str_option(options, 'direction', DEFAULT_DIRECTION)
                    full_width = parser.get_bool_option(options, 'full-width', False)
                    
                    cli.view_operations_by_path(path_prefix, limit, direction, full_width)
                
                elif command == "operations-overview":
                    direction = parser.get_str_option(options, 'direction', DEFAULT_DIRECTION)
                    cli.operations_overview(direction)
                
                elif command == "count-operations":
                    cli.count_operations()
                
                elif command == "count-operations-by-path":
                    if len(positional) < 1:
                        print("Usage: count-operations-by-path <path_prefix> [--direction forward|backward|both]")
                        continue
                    
                    path_prefix = positional[0]
                    direction = parser.get_str_option(options, 'direction', DEFAULT_DIRECTION)
                    cli.count_operations_by_path(path_prefix, direction)
                
                # Advanced commands
                elif command == "ritf":
                    if ritf:
                        print("\nReplayInterface object is available as 'ritf'")
                        print(f"Type: {type(ritf)}")
                        try:
                            print(f"Current time: {ritf.current_time}")
                            print(f"Game ID: {ritf.game_id}")
                            print(f"Player ID: {ritf.player_id}")
                            print("\nYou can access:")
                            print("  ritf.game_state - Current game state")
                            print("  ritf.jump_to(datetime) - Jump to timestamp")
                            print("  ritf.jump_to_next_patch() - Jump forward")
                            print("  ritf.jump_to_previous_patch() - Jump backward")
                            print("  ritf.get_timestamps() - Get all timestamps")
                        except AttributeError as e:
                            print(f"\nWarning: Some attributes not available: {e}")
                    else:
                        print("Error: ritf not available")
                
                elif command == "python":
                    print("\nEntering Python REPL. 'ritf' is available.")
                    print("Use Ctrl-D (Unix) or Ctrl-Z (Windows) to exit.\n")
                    try:
                        import code
                        code.interact(local={'ritf': ritf, 'cli': cli})
                    except Exception as e:
                        print(f"Error: {e}")

                elif command == "check-timestamps":
                    try:
                        cli.check_timestamps()
                    except Exception as e:
                        print(f"Error during timestamp validation: {e}")
                
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
