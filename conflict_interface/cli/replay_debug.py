#!/usr/bin/env python3
"""
Replay Debug CLI Tool

A command-line tool for debugging and inspecting replay files.
Provides commands to open replays, list patches, view patch operations,
and count operations by path.
"""
import argparse
import os
import readline
import shlex
import sys
from datetime import datetime, UTC
from typing import Optional, List, Tuple

from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import ReplayPatch

# Constants for column widths and formatting
COLUMN_WIDTH_INDEX = 5
COLUMN_WIDTH_PATCH = 25
COLUMN_WIDTH_PATCH_FULL = 30
COLUMN_WIDTH_DIRECTION = 8
COLUMN_WIDTH_TYPE = 8
COLUMN_WIDTH_PATH_COMPACT = 35
COLUMN_WIDTH_PATH_FULL = 60
COLUMN_WIDTH_VALUE_COMPACT = 15
COLUMN_WIDTH_TIMESTAMP = 20
COLUMN_WIDTH_OPS = 8
COLUMN_WIDTH_STATE = 35
COLUMN_WIDTH_COUNT = 10

# Default values
DEFAULT_LIMIT = 50
DEFAULT_DIRECTION = 'both'

# Shell prompt
SHELL_PROMPT = "replay-debug> "

# Separator widths
SEPARATOR_WIDTH_COMPACT = 100
SEPARATOR_WIDTH_FULL = 150
SEPARATOR_WIDTH_OVERVIEW = 90


class ReplayDebugCLI:
    """CLI for debugging replay files."""
    
    def __init__(self, filename: str):
        """Initialize the CLI with a replay file.
        
        Args:
            filename: Path to the replay database file
        """
        self.filename = filename
        self.replay: Optional[Replay] = None
        self.all_patches: List[Tuple[int, int, ReplayPatch]] = []
    
    def open_replay(self) -> bool:
        """Open the replay file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.replay = Replay(self.filename, 'r')
            self.replay.open()
            # Load all patches into memory for easier access
            self._load_all_patches()
            return True
        except FileNotFoundError:
            print(f"Error: Replay file '{self.filename}' not found.")
            return False
        except Exception as e:
            print(f"Error opening replay: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_all_patches(self):
        """Load all patches from the database into memory."""
        # Read all patches directly from database
        patches_dict = self.replay.db.read_patches()
        for (from_ts, to_ts), patch in patches_dict.items():
            self.all_patches.append((from_ts, to_ts, patch))
        # Sort by from_timestamp, then to_timestamp
        self.all_patches.sort(key=lambda x: (x[0], x[1]))
    
    def close_replay(self):
        """Close the replay file."""
        if self.replay:
            self.replay.close()
    
    def list_patches(self):
        """List all patches in the replay."""
        if not self.replay:
            print("Error: Replay not opened.")
            return
        
        if not self.all_patches:
            print("No patches found in replay.")
            return
        
        print(f"\nReplay file: {self.filename}")
        print(f"Total patches: {len(self.all_patches)}")
        print(f"Start time: {self.replay.start_time}")
        print(f"End time: {self.replay.last_time}")
        print("\nAll patches (including forward and backward):")
        print("Note: Use 'vp <index>' to view a patch by its index number")
        print("-" * SEPARATOR_WIDTH_COMPACT)
        print(f"{'#':<{COLUMN_WIDTH_INDEX}} {'From Timestamp':<{COLUMN_WIDTH_TIMESTAMP}} {'To Timestamp':<{COLUMN_WIDTH_TIMESTAMP}} {'Direction':<{COLUMN_WIDTH_DIRECTION}} {'Ops':<{COLUMN_WIDTH_OPS}}")
        print("-" * SEPARATOR_WIDTH_COMPACT)
        
        for i, (from_ts, to_ts, patch) in enumerate(self.all_patches):
            from_dt = datetime.fromtimestamp(from_ts / 1000, tz=UTC).isoformat()
            to_dt = datetime.fromtimestamp(to_ts / 1000, tz=UTC).isoformat()
            direction = "Forward" if to_ts > from_ts else "Backward"
            print(f"{i+1:<{COLUMN_WIDTH_INDEX}} {from_dt:<{COLUMN_WIDTH_TIMESTAMP}} {to_dt:<{COLUMN_WIDTH_TIMESTAMP}} {direction:<{COLUMN_WIDTH_DIRECTION}} {len(patch.operations):<{COLUMN_WIDTH_OPS}}")
    
    def view_patch(self, from_timestamp: int, to_timestamp: int):
        """View operations in a specific patch.
        
        Args:
            from_timestamp: Starting timestamp
            to_timestamp: Ending timestamp
        """
        if not self.replay:
            print("Error: Replay not opened.")
            return
        
        # Find the patch
        patch = None
        for from_ts, to_ts, p in self.all_patches:
            if from_ts == from_timestamp and to_ts == to_timestamp:
                patch = p
                break
        
        if not patch:
            print(f"Error: No patch found from {from_timestamp} to {to_timestamp}")
            return
        
        self._display_patch_details(from_timestamp, to_timestamp, patch)
    
    def view_patch_by_index(self, index: int):
        """View operations in a patch by its index from list_patches.
        
        Args:
            index: 1-based index of the patch (as shown in list_patches)
        """
        if not self.replay:
            print("Error: Replay not opened.")
            return
        
        if not self.all_patches:
            print("No patches found in replay.")
            return
        
        if index < 1 or index > len(self.all_patches):
            print(f"Error: Invalid patch index {index}. Valid range: 1-{len(self.all_patches)}")
            return
        
        from_ts, to_ts, patch = self.all_patches[index - 1]
        self._display_patch_details(from_ts, to_ts, patch)
    
    def _display_patch_details(self, from_timestamp: int, to_timestamp: int, patch: ReplayPatch):
        """Display details of a specific patch.
        
        Args:
            from_timestamp: Starting timestamp
            to_timestamp: Ending timestamp
            patch: The ReplayPatch object to display
        """
        direction = "Forward" if to_timestamp > from_timestamp else "Backward"
        
        print(f"\nPatch: {from_timestamp} -> {to_timestamp} ({direction})")
        print(f"From: {datetime.fromtimestamp(from_timestamp / 1000, tz=UTC).isoformat()}")
        print(f"To:   {datetime.fromtimestamp(to_timestamp / 1000, tz=UTC).isoformat()}")
        print(f"Total operations: {len(patch.operations)}")
        print("\nOperations by type:")
        print("-" * 80)
        
        # Count operations by type
        add_count = sum(1 for op in patch.operations if op.Key == 'a')
        replace_count = sum(1 for op in patch.operations if op.Key == 'p')
        remove_count = sum(1 for op in patch.operations if op.Key == 'r')
        
        print(f"  Add:     {add_count}")
        print(f"  Replace: {replace_count}")
        print(f"  Remove:  {remove_count}")
        print()
        
        # Display first 20 operations
        print("First 20 operations:")
        print("-" * 80)
        for i, op in enumerate(patch.operations[:20]):
            path_str = "/".join(str(p) for p in op.path)
            value_str = str(op.new_value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            print(f"{i+1:4d}. {op.Key:7s} {path_str:40s} -> {value_str}")
        
        if len(patch.operations) > 20:
            print(f"\n... and {len(patch.operations) - 20} more operations")
    
    def view_operations_by_path(self, path_prefix: str, limit: int = DEFAULT_LIMIT, direction: str = DEFAULT_DIRECTION, full_width: bool = False):
        """View all operations that start with a specific path across all patches.
        
        Args:
            path_prefix: Path prefix to filter by
            limit: Maximum number of operations to display (default: DEFAULT_LIMIT)
            direction: Direction filter - 'both', 'forward', or 'backward' (default: DEFAULT_DIRECTION)
            full_width: If True, don't truncate paths and values (default: False)
        """
        if not self.replay:
            print("Error: Replay not opened.")
            return
        
        if not self.all_patches:
            print("No patches found in replay.")
            return
        
        # Parse the path prefix
        path_parts = path_prefix.split("/") if path_prefix else []
        
        matching_operations = []
        
        # Collect all matching operations from all patches
        for from_ts, to_ts, patch in self.all_patches:
            is_forward = to_ts > from_ts
            
            # Apply direction filter
            if direction == 'forward' and not is_forward:
                continue
            elif direction == 'backward' and is_forward:
                continue
                
            direction_label = "Forward" if is_forward else "Backward"
            for op in patch.operations:
                if self._path_starts_with(op.path, path_parts):
                    matching_operations.append({
                        'from_ts': from_ts,
                        'to_ts': to_ts,
                        'direction': direction_label,
                        'operation': op
                    })
        
        if not matching_operations:
            print(f"\nNo operations found with path starting with: {path_prefix}")
            return
        
        # Create appropriate filter text
        if direction == 'forward':
            filter_text = " (forward patches only)"
        elif direction == 'backward':
            filter_text = " (backward patches only)"
        else:
            filter_text = ""
            
        print(f"\nOperations with path starting with: '{path_prefix}'{filter_text}")
        print(f"Total matching operations: {len(matching_operations)}")
        print(f"Showing first {min(limit, len(matching_operations))} operations:")
        
        if full_width:
            # Full width output - no truncation
            print("-" * SEPARATOR_WIDTH_FULL)
            print(f"{'#':<{COLUMN_WIDTH_INDEX}} {'Patch':<{COLUMN_WIDTH_PATCH_FULL}} {'Dir':<{COLUMN_WIDTH_DIRECTION}} {'Type':<{COLUMN_WIDTH_TYPE}} {'Path':<{COLUMN_WIDTH_PATH_FULL}} {'Value'}")
            print("-" * SEPARATOR_WIDTH_FULL)
            
            for i, match in enumerate(matching_operations[:limit]):
                from_dt = datetime.fromtimestamp(match['from_ts'] / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
                op = match['operation']
                path_str = "/".join(str(p) for p in op.path)
                value_str = str(op.new_value)
                
                patch_label = f"{match['from_ts']}→{match['to_ts']}"
                if len(patch_label) > COLUMN_WIDTH_PATCH_FULL:
                    patch_label = f"...{patch_label[-(COLUMN_WIDTH_PATCH_FULL-3):]}"
                
                # For full width, still limit path for readability, but show full value
                if len(path_str) > COLUMN_WIDTH_PATH_FULL:
                    path_str = path_str[:(COLUMN_WIDTH_PATH_FULL-3)] + "..."
                
                print(f"{i+1:<{COLUMN_WIDTH_INDEX}} {patch_label:<{COLUMN_WIDTH_PATCH_FULL}} {match['direction']:<{COLUMN_WIDTH_DIRECTION}} {op.Key:<{COLUMN_WIDTH_TYPE}} {path_str:<{COLUMN_WIDTH_PATH_FULL}} {value_str}")
        else:
            # Compact output with truncation
            print("-" * SEPARATOR_WIDTH_COMPACT)
            print(f"{'#':<{COLUMN_WIDTH_INDEX}} {'Patch':<{COLUMN_WIDTH_PATCH}} {'Dir':<{COLUMN_WIDTH_DIRECTION}} {'Type':<{COLUMN_WIDTH_TYPE}} {'Path':<{COLUMN_WIDTH_PATH_COMPACT}} {'Value':<{COLUMN_WIDTH_VALUE_COMPACT}}")
            print("-" * SEPARATOR_WIDTH_COMPACT)
            
            for i, match in enumerate(matching_operations[:limit]):
                from_dt = datetime.fromtimestamp(match['from_ts'] / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
                op = match['operation']
                path_str = "/".join(str(p) for p in op.path)
                if len(path_str) > COLUMN_WIDTH_PATH_COMPACT:
                    path_str = path_str[:(COLUMN_WIDTH_PATH_COMPACT-3)] + "..."
                value_str = str(op.new_value)
                if len(value_str) > COLUMN_WIDTH_VALUE_COMPACT:
                    value_str = value_str[:(COLUMN_WIDTH_VALUE_COMPACT-3)] + "..."
                
                patch_label = f"{match['from_ts']}→{match['to_ts']}"
                if len(patch_label) > COLUMN_WIDTH_PATCH:
                    patch_label = f"...{patch_label[-(COLUMN_WIDTH_PATCH-3):]}"
                
                print(f"{i+1:<{COLUMN_WIDTH_INDEX}} {patch_label:<{COLUMN_WIDTH_PATCH}} {match['direction']:<{COLUMN_WIDTH_DIRECTION}} {op.Key:<{COLUMN_WIDTH_TYPE}} {path_str:<{COLUMN_WIDTH_PATH_COMPACT}} {value_str:<{COLUMN_WIDTH_VALUE_COMPACT}}")
        
        if len(matching_operations) > limit:
            print(f"\n... and {len(matching_operations) - limit} more operations")
    
    def count_operations(self):
        """Count total number of operations across all patches."""
        if not self.replay:
            print("Error: Replay not opened.")
            return
        
        if not self.all_patches:
            print("No patches found in replay.")
            return
        
        total_operations = 0
        forward_patches = 0
        backward_patches = 0
        forward_ops = 0
        backward_ops = 0
        
        for from_ts, to_ts, patch in self.all_patches:
            ops_count = len(patch.operations)
            total_operations += ops_count
            
            if to_ts > from_ts:
                forward_patches += 1
                forward_ops += ops_count
            else:
                backward_patches += 1
                backward_ops += ops_count
        
        print(f"\nTotal patches: {len(self.all_patches)}")
        print(f"  Forward patches:  {forward_patches}")
        print(f"  Backward patches: {backward_patches}")
        print(f"\nTotal operations: {total_operations}")
        print(f"  Forward operations:  {forward_ops}")
        print(f"  Backward operations: {backward_ops}")
        
        if len(self.all_patches) > 0:
            print(f"\nAverage operations per patch: {total_operations / len(self.all_patches):.2f}")
    
    def count_operations_by_path(self, path_prefix: str, direction: str = 'both'):
        """Count operations that start with a specific path.
        
        Args:
            path_prefix: Path prefix to filter by
            direction: Direction filter - 'both', 'forward', or 'backward' (default: 'both')
        """
        if not self.replay:
            print("Error: Replay not opened.")
            return
        
        if not self.all_patches:
            print("No patches found in replay.")
            return
        
        # Parse the path prefix
        path_parts = path_prefix.split("/") if path_prefix else []
        
        matching_operations = 0
        total_operations = 0
        matching_forward = 0
        matching_backward = 0
        
        for from_ts, to_ts, patch in self.all_patches:
            is_forward = to_ts > from_ts
            
            # Apply direction filter
            if direction == 'forward' and not is_forward:
                continue
            elif direction == 'backward' and is_forward:
                continue
                
            for op in patch.operations:
                total_operations += 1
                # Check if operation path starts with the given prefix
                if self._path_starts_with(op.path, path_parts):
                    matching_operations += 1
                    if is_forward:
                        matching_forward += 1
                    else:
                        matching_backward += 1
        
        # Create appropriate filter text
        if direction == 'forward':
            filter_text = " (forward patches only)"
        elif direction == 'backward':
            filter_text = " (backward patches only)"
        else:
            filter_text = ""
            
        print(f"\nPath prefix: '{path_prefix}'{filter_text}")
        
        # Count patches based on direction filter
        if direction == 'forward':
            patch_count = sum(1 for from_ts, to_ts, _ in self.all_patches if to_ts > from_ts)
        elif direction == 'backward':
            patch_count = sum(1 for from_ts, to_ts, _ in self.all_patches if to_ts < from_ts)
        else:
            patch_count = len(self.all_patches)
            
        print(f"Total patches analyzed: {patch_count}")
        print(f"Total operations: {total_operations}")
        print(f"Matching operations: {matching_operations}")
        
        # Only show breakdown if analyzing both directions
        if direction == 'both':
            print(f"  In forward patches:  {matching_forward}")
            print(f"  In backward patches: {matching_backward}")
        
        if total_operations > 0:
            percentage = (matching_operations / total_operations) * 100
            print(f"Percentage: {percentage:.2f}%")
    
    def operations_overview(self, direction: str = 'both'):
        """Show an overview of operations grouped by state and operation type.
        
        Args:
            direction: Direction filter - 'both', 'forward', or 'backward' (default: 'both')
        """
        if not self.replay:
            print("Error: Replay not opened.")
            return
        
        if not self.all_patches:
            print("No patches found in replay.")
            return
        
        # Dictionary to store counts: {state_path: {op_type: count}}
        state_stats = {}
        total_ops = 0
        
        # Collect statistics
        for from_ts, to_ts, patch in self.all_patches:
            is_forward = to_ts > from_ts
            
            # Apply direction filter
            if direction == 'forward' and not is_forward:
                continue
            elif direction == 'backward' and is_forward:
                continue
            
            for op in patch.operations:
                total_ops += 1
                
                # Extract the state path (first level after 'states' or root if not under 'states')
                if len(op.path) > 0:
                    if op.path[0] == "states" and len(op.path) > 1:
                        state_name = f"states/{op.path[1]}"
                    else:
                        state_name = op.path[0]
                else:
                    state_name = "<root>"
                
                # Initialize state if not seen before
                if state_name not in state_stats:
                    state_stats[state_name] = {'a': 0, 'p': 0, 'r': 0}
                
                # Count operation by type
                state_stats[state_name][op.Key] += 1
        
        # Display results
        if direction == 'forward':
            filter_text = " (forward patches only)"
        elif direction == 'backward':
            filter_text = " (backward patches only)"
        else:
            filter_text = ""
            
        print(f"\nOperations Overview{filter_text}")
        print("=" * SEPARATOR_WIDTH_OVERVIEW)
        
        # Count patches based on direction filter
        if direction == 'forward':
            patch_count = sum(1 for from_ts, to_ts, _ in self.all_patches if to_ts > from_ts)
            direction_label = "forward only"
        elif direction == 'backward':
            patch_count = sum(1 for from_ts, to_ts, _ in self.all_patches if to_ts < from_ts)
            direction_label = "backward only"
        else:
            patch_count = len(self.all_patches)
            direction_label = "forward + backward"
            
        print(f"Analyzed patches: {patch_count} ({direction_label})")
        
        print(f"Total operations: {total_ops}")
        print()
        print(f"{'State':<{COLUMN_WIDTH_STATE}} {'Add':<{COLUMN_WIDTH_COUNT}} {'Replace':<{COLUMN_WIDTH_COUNT}} {'Remove':<{COLUMN_WIDTH_COUNT}} {'Total':<{COLUMN_WIDTH_COUNT}}")
        print("-" * SEPARATOR_WIDTH_OVERVIEW)
        
        # Sort states by total operations (descending)
        sorted_states = sorted(
            state_stats.items(),
            key=lambda x: sum(x[1].values()),
            reverse=True
        )
        
        for state_name, counts in sorted_states:
            add_count = counts['a']
            replace_count = counts['p']
            remove_count = counts['r']
            total_count = add_count + replace_count + remove_count
            
            print(f"{state_name:<{COLUMN_WIDTH_STATE}} {add_count:<{COLUMN_WIDTH_COUNT}} {replace_count:<{COLUMN_WIDTH_COUNT}} {remove_count:<{COLUMN_WIDTH_COUNT}} {total_count:<{COLUMN_WIDTH_COUNT}}")
        
        print("-" * SEPARATOR_WIDTH_OVERVIEW)
        
        # Summary totals
        total_add = sum(counts['a'] for counts in state_stats.values())
        total_replace = sum(counts['p'] for counts in state_stats.values())
        total_remove = sum(counts['r'] for counts in state_stats.values())
        
        print(f"{'TOTAL':<{COLUMN_WIDTH_STATE}} {total_add:<{COLUMN_WIDTH_COUNT}} {total_replace:<{COLUMN_WIDTH_COUNT}} {total_remove:<{COLUMN_WIDTH_COUNT}} {total_ops:<{COLUMN_WIDTH_COUNT}}")
    
    def interactive_shell(self):
        """Run an interactive shell for executing commands."""
        # Enable readline for command history (arrow keys)
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
            import atexit
            atexit.register(readline.write_history_file, histfile)
        except ImportError:
            # readline not available on this platform
            pass
        
        print(f"\nReplay Debug Shell - {self.filename}")
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
                    self._print_interactive_help()
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
                        self.list_patches()
                    
                    elif command == "view-patch" or command == "vp":
                        if len(args) < 2:
                            print("Usage: view-patch <index> OR view-patch <from_timestamp> <to_timestamp>")
                            continue
                        
                        # Check if single argument (index) or two arguments (timestamps)
                        if len(args) == 2:
                            # Single argument - treat as index
                            try:
                                index = int(args[1])
                                self.view_patch_by_index(index)
                            except ValueError:
                                print("Error: Index must be an integer")
                        else:
                            # Two arguments - treat as timestamps
                            try:
                                from_ts = int(args[1])
                                to_ts = int(args[2])
                                self.view_patch(from_ts, to_ts)
                            except ValueError:
                                print("Error: Timestamps must be integers")
                    
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
                        
                        self.view_operations_by_path(path_prefix, limit, direction, full_width)
                    
                    elif command == "operations-overview" or command == "oo":
                        direction = DEFAULT_DIRECTION
                        if '--direction' in args:
                            idx = args.index('--direction')
                            if idx + 1 < len(args):
                                direction = args[idx + 1]
                        
                        self.operations_overview(direction)
                    
                    elif command == "count-operations" or command == "co":
                        self.count_operations()
                    
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
                        
                        self.count_operations_by_path(path_prefix, direction)
                    
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
    
    def _print_interactive_help(self):
        """Print help for interactive mode."""
        print("""
Available Commands:
  list-patches (lp)                           - List all patches with indices
  view-patch (vp) <index>                     - View a patch by its index number
  view-patch (vp) <from_ts> <to_ts>           - View a specific patch by timestamps
  view-operations-by-path (vop) <path> [opts] - View operations by path
    Options: --limit N, --direction forward|backward|both, --full-width
  operations-overview (oo) [--direction ...]  - Show operations overview
  count-operations (co)                       - Count all operations
  count-operations-by-path (cop) <path> [...] - Count operations by path
    Options: --direction forward|backward|both
  help (?)                                    - Show this help
  exit, quit, q                               - Exit the shell

Navigation:
  - Use UP/DOWN arrow keys to cycle through command history
  - After 'list-patches', use 'vp <index>' to quickly view a patch

Examples:
  list-patches
  vp 1                                         # View first patch from list
  vop "states/map_state" --direction forward --full-width
  oo --direction forward
  cop "states/player_state"
        """)

    
    def _path_starts_with(self, path: list, prefix: list) -> bool:
        """Check if a path starts with a given prefix.
        
        Args:
            path: Operation path as list
            prefix: Prefix to check as list
            
        Returns:
            True if path starts with prefix, False otherwise
        """
        if not prefix:
            return True
        if len(path) < len(prefix):
            return False
        for i, part in enumerate(prefix):
            if str(path[i]) != str(part):
                return False
        return True


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
            cli.interactive_shell()
            return 0
        
        # Otherwise, execute the single command
        # Re-parse with the command as first argument of remaining
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
