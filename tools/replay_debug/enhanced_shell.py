"""
Enhanced interactive shell for the Replay Debug CLI Tool.

This shell supports both the original patch analysis CLI and the new
enhanced CLI with ReplayInterface integration for live state inspection.
"""
import os
import shlex
import atexit
from typing import Union

from .constants import *
from .cli import ReplayDebugCLI
from .enhanced_cli import EnhancedReplayDebugCLI


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


def print_enhanced_help():
    """Print help for enhanced interactive mode."""
    print("""
Available Commands:

Patch Analysis (Original CLI):
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

Navigation (Enhanced Mode):
  info                                        - Display current replay position
  jump-relative (jr) <seconds>                - Jump by relative time (e.g., jr 60 for +1 min)
  jump-absolute (ja) <timestamp>              - Jump to absolute time (ISO format)
  jump-patches (jp) <num>                     - Jump by number of patches (e.g., jp -5)
  jump-index (ji) <index>                     - Jump to timestamp by index
  list-timestamps (lt) [--limit N]            - List all timestamps with indices

State Viewing (Enhanced Mode):
  view-state (vs) <path> [--depth N]          - View game state at path
  list-states (ls)                            - List available state categories
  search-paths (sp) <term>                    - Search for paths containing term

Advanced:
  ritf                                        - Access ReplayInterface object in Python
  python                                      - Enter Python REPL with ritf available
  help (?)                                    - Show this help
  exit, quit, q                               - Exit the shell

Navigation:
  - Use UP/DOWN arrow keys to cycle through command history
  - Enhanced mode provides live game state inspection
  - Use 'ritf' to access the ReplayInterface object directly

Examples:
  jr 60                      # Jump forward 60 seconds
  jp -5                      # Jump back 5 patches
  ji 100                     # Jump to timestamp index 100
  vs states/map_state        # View map state
  sp "player"                # Search for paths containing "player"
        """)


def run_enhanced_shell(cli: Union[ReplayDebugCLI, EnhancedReplayDebugCLI]):
    """Run an interactive shell with enhanced features.
    
    Args:
        cli: ReplayDebugCLI or EnhancedReplayDebugCLI instance
    """
    setup_readline()
    
    # Determine if we're using enhanced mode
    is_enhanced = isinstance(cli, EnhancedReplayDebugCLI)
    
    print(f"\nReplay Debug Shell {'(Enhanced Mode)' if is_enhanced else ''} - {cli.filename}")
    print("Type 'help' for available commands, 'exit' or 'quit' to exit\n")
    
    # Make ritf available for advanced usage
    ritf = cli.get_ritf() if is_enhanced else None
    
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
                if is_enhanced:
                    print_enhanced_help()
                else:
                    from .shell import print_interactive_help
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
            
            # Execute enhanced mode commands
            if is_enhanced:
                if command == "info":
                    cli.display_info()
                    continue
                
                elif command == "jump-relative" or command == "jr":
                    if len(args) < 2:
                        print("Usage: jump-relative <seconds>")
                        continue
                    try:
                        seconds = float(args[1])
                        cli.jump_relative(seconds)
                    except ValueError:
                        print("Error: seconds must be a number")
                    continue
                
                elif command == "jump-absolute" or command == "ja":
                    if len(args) < 2:
                        print("Usage: jump-absolute <timestamp>")
                        continue
                    cli.jump_absolute(args[1])
                    continue
                
                elif command == "jump-patches" or command == "jp":
                    if len(args) < 2:
                        print("Usage: jump-patches <num>")
                        continue
                    try:
                        num = int(args[1])
                        cli.jump_patches(num)
                    except ValueError:
                        print("Error: num must be an integer")
                    continue
                
                elif command == "jump-index" or command == "ji":
                    if len(args) < 2:
                        print("Usage: jump-index <index>")
                        continue
                    try:
                        index = int(args[1])
                        cli.jump_index(index)
                    except ValueError:
                        print("Error: index must be an integer")
                    continue
                
                elif command == "list-timestamps" or command == "lt":
                    limit = 50
                    if '--limit' in args:
                        idx = args.index('--limit')
                        if idx + 1 < len(args):
                            try:
                                limit = int(args[idx + 1])
                            except ValueError:
                                print("Error: --limit value must be an integer")
                                continue
                    cli.list_timestamps(limit)
                    continue
                
                elif command == "view-state" or command == "vs":
                    if len(args) < 2:
                        print("Usage: view-state <path> [--depth N]")
                        continue
                    
                    path = args[1]
                    max_depth = 5
                    
                    if '--depth' in args:
                        idx = args.index('--depth')
                        if idx + 1 < len(args):
                            try:
                                max_depth = int(args[idx + 1])
                            except ValueError:
                                print("Error: --depth value must be an integer")
                                continue
                    
                    cli.view_state_path(path, max_depth)
                    continue
                
                elif command == "list-states" or command == "ls":
                    cli.list_states()
                    continue
                
                elif command == "search-paths" or command == "sp":
                    if len(args) < 2:
                        print("Usage: search-paths <term>")
                        continue
                    cli.search_paths(args[1])
                    continue
                
                elif command == "ritf":
                    if ritf:
                        print("\nReplayInterface object is available as 'ritf'")
                        print(f"Type: {type(ritf)}")
                        print(f"Current time: {ritf.current_time}")
                        print(f"Game ID: {ritf.game_id}")
                        print(f"Player ID: {ritf.player_id}")
                        print("\nYou can access:")
                        print("  ritf.game_state - Current game state")
                        print("  ritf.jump_to(datetime) - Jump to timestamp")
                        print("  ritf.jump_to_next_patch() - Jump forward")
                        print("  ritf.jump_to_previous_patch() - Jump backward")
                        print("  ritf.get_timestamps() - Get all timestamps")
                    else:
                        print("Error: ritf not available")
                    continue
                
                elif command == "python":
                    print("\nEntering Python REPL. 'ritf' is available.")
                    print("Use Ctrl-D (Unix) or Ctrl-Z (Windows) to exit.\n")
                    try:
                        import code
                        code.interact(local={'ritf': ritf, 'cli': cli})
                    except Exception as e:
                        print(f"Error: {e}")
                    continue
            
            # Execute original CLI commands
            # These work in both modes, but use the original CLI methods
            try:
                if command == "list-patches" or command == "lp":
                    if hasattr(cli, 'list_patches'):
                        cli.list_patches()
                    else:
                        print("Command not available in enhanced mode. Use original mode for patch analysis.")
                
                elif command == "view-patch" or command == "vp":
                    if not hasattr(cli, 'view_patch'):
                        print("Command not available in enhanced mode. Use original mode for patch analysis.")
                        continue
                    
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
                    if hasattr(cli, 'display_metadata'):
                        cli.display_metadata()
                    else:
                        cli.display_info()
                
                elif command == "view-operations-by-path" or command == "vop":
                    if not hasattr(cli, 'view_operations_by_path'):
                        print("Command not available in enhanced mode. Use original mode for patch analysis.")
                        continue
                    
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
                    if not hasattr(cli, 'operations_overview'):
                        print("Command not available in enhanced mode. Use original mode for patch analysis.")
                        continue
                    
                    direction = DEFAULT_DIRECTION
                    if '--direction' in args:
                        idx = args.index('--direction')
                        if idx + 1 < len(args):
                            direction = args[idx + 1]
                    
                    cli.operations_overview(direction)
                
                elif command == "count-operations" or command == "co":
                    if not hasattr(cli, 'count_operations'):
                        print("Command not available in enhanced mode. Use original mode for patch analysis.")
                        continue
                    cli.count_operations()
                
                elif command == "count-operations-by-path" or command == "cop":
                    if not hasattr(cli, 'count_operations_by_path'):
                        print("Command not available in enhanced mode. Use original mode for patch analysis.")
                        continue
                    
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
