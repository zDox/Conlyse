#!/usr/bin/env python3
"""
Replay Debug CLI Tool

A command-line tool for debugging and inspecting replay files.
Provides commands to open replays, list patches, view patch operations,
and count operations by path.
"""
import argparse
import os
import shlex
import sys
from datetime import datetime, UTC
from typing import Optional, List, Tuple

from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import ReplayPatch


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
        print("-" * 100)
        print(f"{'#':<5} {'From Timestamp':<20} {'To Timestamp':<20} {'Direction':<10} {'Ops':<8}")
        print("-" * 100)
        
        for i, (from_ts, to_ts, patch) in enumerate(self.all_patches):
            from_dt = datetime.fromtimestamp(from_ts / 1000, tz=UTC).isoformat()
            to_dt = datetime.fromtimestamp(to_ts / 1000, tz=UTC).isoformat()
            direction = "Forward" if to_ts > from_ts else "Backward"
            print(f"{i+1:<5} {from_dt:<20} {to_dt:<20} {direction:<10} {len(patch.operations):<8}")
    
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
    
    def view_operations_by_path(self, path_prefix: str, limit: int = 50, direction: str = 'both', full_width: bool = False):
        """View all operations that start with a specific path across all patches.
        
        Args:
            path_prefix: Path prefix to filter by
            limit: Maximum number of operations to display (default: 50)
            direction: Direction filter - 'both', 'forward', or 'backward' (default: 'both')
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
            print("-" * 150)
            print(f"{'#':<5} {'Patch':<30} {'Dir':<8} {'Type':<8} {'Path':<60} {'Value'}")
            print("-" * 150)
            
            for i, match in enumerate(matching_operations[:limit]):
                from_dt = datetime.fromtimestamp(match['from_ts'] / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
                op = match['operation']
                path_str = "/".join(str(p) for p in op.path)
                value_str = str(op.new_value)
                
                patch_label = f"{match['from_ts']}→{match['to_ts']}"
                if len(patch_label) > 30:
                    patch_label = f"...{patch_label[-27:]}"
                
                # For full width, still limit path to 60 chars for readability, but show full value
                if len(path_str) > 60:
                    path_str = path_str[:57] + "..."
                
                print(f"{i+1:<5} {patch_label:<30} {match['direction']:<8} {op.Key:<8} {path_str:<60} {value_str}")
        else:
            # Compact output with truncation
            print("-" * 100)
            print(f"{'#':<5} {'Patch':<25} {'Dir':<8} {'Type':<8} {'Path':<35} {'Value':<15}")
            print("-" * 100)
            
            for i, match in enumerate(matching_operations[:limit]):
                from_dt = datetime.fromtimestamp(match['from_ts'] / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
                op = match['operation']
                path_str = "/".join(str(p) for p in op.path)
                if len(path_str) > 35:
                    path_str = path_str[:32] + "..."
                value_str = str(op.new_value)
                if len(value_str) > 15:
                    value_str = value_str[:12] + "..."
                
                patch_label = f"{match['from_ts']}→{match['to_ts']}"
                if len(patch_label) > 25:
                    patch_label = f"...{patch_label[-22:]}"
                
                print(f"{i+1:<5} {patch_label:<25} {match['direction']:<8} {op.Key:<8} {path_str:<35} {value_str:<15}")
        
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
        print("=" * 90)
        
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
        print(f"{'State':<35} {'Add':<10} {'Replace':<10} {'Remove':<10} {'Total':<10}")
        print("-" * 90)
        
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
            
            print(f"{state_name:<35} {add_count:<10} {replace_count:<10} {remove_count:<10} {total_count:<10}")
        
        print("-" * 90)
        
        # Summary totals
        total_add = sum(counts['a'] for counts in state_stats.values())
        total_replace = sum(counts['p'] for counts in state_stats.values())
        total_remove = sum(counts['r'] for counts in state_stats.values())
        
        print(f"{'TOTAL':<35} {total_add:<10} {total_replace:<10} {total_remove:<10} {total_ops:<10}")
    
    def interactive_shell(self):
        """Run an interactive shell for executing commands."""
        print(f"\nReplay Debug Shell - {self.filename}")
        print("Type 'help' for available commands, 'exit' or 'quit' to exit\n")
        
        while True:
            try:
                # Get user input
                user_input = input("replay-debug> ").strip()
                
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
                        if len(args) < 3:
                            print("Usage: view-patch <from_timestamp> <to_timestamp>")
                            continue
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
                        limit = 50
                        direction = 'both'
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
                        direction = 'both'
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
                        direction = 'both'
                        
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
  list-patches (lp)                           - List all patches
  view-patch (vp) <from_ts> <to_ts>           - View a specific patch
  view-operations-by-path (vop) <path> [opts] - View operations by path
    Options: --limit N, --direction forward|backward|both, --full-width
  operations-overview (oo) [--direction ...]  - Show operations overview
  count-operations (co)                       - Count all operations
  count-operations-by-path (cop) <path> [...] - Count operations by path
    Options: --direction forward|backward|both
  help (?)                                    - Show this help
  exit, quit, q                               - Exit the shell

Examples:
  list-patches
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
            limit = 50
            direction = 'both'
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
            direction = 'both'
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
            direction = 'both'
            
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
