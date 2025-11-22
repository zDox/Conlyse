"""
Centralized argument parsing for the Replay Debug CLI Tool.

This module provides argument parsing functionality using argparse,
consolidating all command-line argument definitions in one place.
"""
import argparse
import shlex
from typing import List, Optional, Tuple, Dict, Any


class CommandParser:
    """Parser for interactive shell commands."""
    
    @staticmethod
    def parse_command(user_input: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Parse a command string into command name, args, and options.
        
        Args:
            user_input: Raw command string from user
            
        Returns:
            Tuple of (command_name, positional_args, options_dict)
            
        Example:
            >>> parse_command("vp 1 --limit 50")
            ('vp', ['1'], {'limit': 50})
        """
        try:
            tokens = shlex.split(user_input)
        except ValueError as e:
            raise ValueError(f"Error parsing command: {e}")
        
        if not tokens:
            return ("", [], {})
        
        command = tokens[0]
        remaining = tokens[1:]
        
        # Parse options
        options = {}
        positional = []
        
        i = 0
        while i < len(remaining):
            token = remaining[i]
            
            if token.startswith('--'):
                # Long option
                option_name = token[2:]
                
                # Check if next token is the value
                if i + 1 < len(remaining) and not remaining[i + 1].startswith('--'):
                    options[option_name] = remaining[i + 1]
                    i += 2
                else:
                    # Boolean flag
                    options[option_name] = True
                    i += 1
            else:
                # Positional argument
                positional.append(token)
                i += 1
        
        return (command, positional, options)
    
    @staticmethod
    def get_int_option(options: Dict[str, Any], name: str, default: Optional[int] = None) -> Optional[int]:
        """Get an integer option value.
        
        Args:
            options: Options dictionary
            name: Option name
            default: Default value if not present
            
        Returns:
            Integer value or default
            
        Raises:
            ValueError: If value cannot be converted to int
        """
        if name not in options:
            return default
        
        try:
            return int(options[name])
        except (ValueError, TypeError):
            raise ValueError(f"Option --{name} must be an integer")
    
    @staticmethod
    def get_str_option(options: Dict[str, Any], name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a string option value.
        
        Args:
            options: Options dictionary
            name: Option name
            default: Default value if not present
            
        Returns:
            String value or default
        """
        return options.get(name, default)
    
    @staticmethod
    def get_bool_option(options: Dict[str, Any], name: str, default: bool = False) -> bool:
        """Get a boolean option value.
        
        Args:
            options: Options dictionary
            name: Option name
            default: Default value if not present
            
        Returns:
            Boolean value or default
        """
        return bool(options.get(name, default))


class MainArgumentParser:
    """Parser for main CLI arguments."""
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create and configure the main argument parser.
        
        Returns:
            Configured ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            description="Replay Debug CLI Tool - Inspect and debug replay files",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Interactive Mode (Recommended):
  Start the interactive shell for full access to all features:
    %(prog)s replay.db

  Available commands in interactive mode:
    - Navigation: jr, ja, jp, ji, lt (jump and list)
    - State viewing: vs, ls, sp (view and search)
    - Patch analysis: lp, vp, vop, oo, co, cop
    - Advanced: ritf, python, info, help

Examples:
  %(prog)s replay.db                    # Start interactive mode
  %(prog)s replay.db --help             # Show this help
  
Interactive Shell Examples:
  replay-debug> jr 60                   # Jump forward 60 seconds
  replay-debug> vs states/player_state  # View player state
  replay-debug> lp                      # List all patches
  replay-debug> python                  # Enter Python REPL with ritf
            """
        )
        
        parser.add_argument(
            "replay_file",
            help="Path to the replay database file (.db)"
        )
        
        return parser


# Command aliases mapping
COMMAND_ALIASES = {
    # Navigation
    'jr': 'jump-relative',
    'ja': 'jump-absolute',
    'jp': 'jump-patches',
    'ji': 'jump-index',
    'lt': 'list-timestamps',
    
    # Game Object viewing
    'vg': 'view-game-object',
    'ls': 'list-states',
    'sp': 'search-paths',
    
    # Patch analysis
    'lp': 'list-patches',
    'vp': 'view-patch',
    'vop': 'view-operations-by-path',
    'oo': 'operations-overview',
    'co': 'count-operations',
    'cop': 'count-operations-by-path',
    
    # Metadata
    'md': 'metadata',
    
    # Help
    '?': 'help',
    'q': 'quit',
}


def resolve_alias(command: str) -> str:
    """Resolve command alias to full command name.
    
    Args:
        command: Command name or alias
        
    Returns:
        Full command name
    """
    return COMMAND_ALIASES.get(command, command)
