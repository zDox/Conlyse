"""
Interactive shell for the Replay Debug CLI Tool.

This module provides a unified interactive shell that supports all features:
navigation, state viewing, and patch analysis.

Uses the command registry for automatic command dispatch.
"""
import os
import atexit

from .constants import *
from .cli import ReplayDebugCLI
from .args_parser import CommandParser
from .command_registry import CommandRegistry, CommandExecutor

# Import commands to register them
import tools.replay_debug.commands  # noqa: F401


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
    """Print help for interactive mode from registered commands."""
    registry = CommandRegistry.get_instance()
    commands = registry.get_all_commands()
    
    # Group commands by category (based on their name prefix or order of registration)
    navigation_cmds = ['info', 'jump-relative', 'jump-absolute', 'jump-patches', 'jump-index', 'list-timestamps']
    state_cmds = ['view-state', 'list-states', 'search-paths']
    patch_cmds = ['list-patches', 'view-patch', 'view-operations-by-path', 'operations-overview', 
                  'count-operations', 'count-operations-by-path', 'metadata', 'check-timestamps']
    advanced_cmds = ['ritf', 'python']
    
    print("\nAvailable Commands:\n")
    
    def print_cmd_group(title, cmd_names):
        print(f"{title}:")
        for name in cmd_names:
            cmd = commands.get(name)
            if cmd:
                aliases_str = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
                usage = cmd.usage if cmd.usage else name
                desc = cmd.description if cmd.description else ""
                print(f"  {usage}{aliases_str}")
                if desc:
                    print(f"      {desc}")
        print()
    
    print_cmd_group("Navigation", navigation_cmds)
    print_cmd_group("State Viewing", state_cmds)
    print_cmd_group("Patch Analysis", patch_cmds)
    print_cmd_group("Advanced", advanced_cmds)
    
    print("Shell Commands:")
    print("  help (?)                                    - Show this help")
    print("  exit, quit, q                               - Exit the shell")
    print()
    print("Examples:")
    print("  jr 60                       # Jump forward 60 seconds")
    print("  vs states/player_state      # View player state")
    print("  lp                          # List all patches")
    print("  vp 1 --limit 50            # View first 50 operations of patch 1")
    print("  python                      # Enter Python REPL")


def run_interactive_shell(cli: ReplayDebugCLI):
    """Run an interactive shell for executing commands.
    
    Args:
        cli: ReplayDebugCLI instance
    """
    setup_readline()
    
    parser = CommandParser()
    executor = CommandExecutor()
    
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
            
            # Try to execute the command using the registry
            if not executor.execute(command, positional, options, context=cli):
                print(f"Unknown command: {command}")
                print("Type 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\nUse 'exit' or 'quit' to exit")
            continue
        except EOFError:
            print("\nExiting...")
            break
