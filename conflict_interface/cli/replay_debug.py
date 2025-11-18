#!/usr/bin/env python3
"""
Replay Debug CLI Tool

A command-line tool for debugging and inspecting replay files.
Provides commands to open replays, list patches, view patch operations,
and count operations by path.
"""
import argparse
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
    
    def view_operations_by_path(self, path_prefix: str, limit: int = 50, forward_only: bool = False):
        """View all operations that start with a specific path across all patches.
        
        Args:
            path_prefix: Path prefix to filter by
            limit: Maximum number of operations to display (default: 50)
            forward_only: If True, only include operations from forward patches (default: False)
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
            
            # Skip backward patches if forward_only is True
            if forward_only and not is_forward:
                continue
                
            direction = "Forward" if is_forward else "Backward"
            for op in patch.operations:
                if self._path_starts_with(op.path, path_parts):
                    matching_operations.append({
                        'from_ts': from_ts,
                        'to_ts': to_ts,
                        'direction': direction,
                        'operation': op
                    })
        
        if not matching_operations:
            print(f"\nNo operations found with path starting with: {path_prefix}")
            return
        
        filter_text = " (forward patches only)" if forward_only else ""
        print(f"\nOperations with path starting with: '{path_prefix}'{filter_text}")
        print(f"Total matching operations: {len(matching_operations)}")
        print(f"Showing first {min(limit, len(matching_operations))} operations:")
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
    
    def count_operations_by_path(self, path_prefix: str, forward_only: bool = False):
        """Count operations that start with a specific path.
        
        Args:
            path_prefix: Path prefix to filter by
            forward_only: If True, only count operations from forward patches (default: False)
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
            
            # Skip backward patches if forward_only is True
            if forward_only and not is_forward:
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
        
        filter_text = " (forward patches only)" if forward_only else ""
        print(f"\nPath prefix: '{path_prefix}'{filter_text}")
        
        if forward_only:
            forward_patch_count = sum(1 for from_ts, to_ts, _ in self.all_patches if to_ts > from_ts)
            print(f"Total patches analyzed: {forward_patch_count}")
        else:
            print(f"Total patches analyzed: {len(self.all_patches)}")
            
        print(f"Total operations: {total_operations}")
        print(f"Matching operations: {matching_operations}")
        
        if not forward_only:
            print(f"  In forward patches:  {matching_forward}")
            print(f"  In backward patches: {matching_backward}")
        
        if total_operations > 0:
            percentage = (matching_operations / total_operations) * 100
            print(f"Percentage: {percentage:.2f}%")
    
    def operations_overview(self, forward_only: bool = False):
        """Show an overview of operations grouped by state and operation type.
        
        Args:
            forward_only: If True, only analyze operations from forward patches (default: False)
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
            
            # Skip backward patches if forward_only is True
            if forward_only and not is_forward:
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
        filter_text = " (forward patches only)" if forward_only else ""
        print(f"\nOperations Overview{filter_text}")
        print("=" * 90)
        
        if forward_only:
            forward_patch_count = sum(1 for from_ts, to_ts, _ in self.all_patches if to_ts > from_ts)
            print(f"Analyzed patches: {forward_patch_count} (forward only)")
        else:
            print(f"Analyzed patches: {len(self.all_patches)} (forward + backward)")
        
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
Examples:
  # Open a replay and list all patches (including forward and backward)
  %(prog)s replay.db list-patches
  
  # View a specific patch
  %(prog)s replay.db view-patch 1638360000000 1638360060000
  
  # View operations starting with a specific path (forward patches only)
  %(prog)s replay.db view-operations-by-path "states/map_state" --forward-only
  
  # Get operations overview by state
  %(prog)s replay.db operations-overview
  
  # Get operations overview for forward patches only
  %(prog)s replay.db operations-overview --forward-only
  
  # Count all operations
  %(prog)s replay.db count-operations
  
  # Count operations starting with a path (forward patches only)
  %(prog)s replay.db count-operations-by-path "states/map_state" --forward-only
        """
    )
    
    parser.add_argument(
        "replay_file",
        help="Path to the replay database file (.db)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # list-patches command
    subparsers.add_parser(
        "list-patches",
        help="List all patches in the replay with timestamps (including forward and backward)"
    )
    
    # view-patch command
    view_parser = subparsers.add_parser(
        "view-patch",
        help="View operations in a specific patch"
    )
    view_parser.add_argument(
        "from_timestamp",
        type=int,
        help="Starting timestamp (in milliseconds)"
    )
    view_parser.add_argument(
        "to_timestamp",
        type=int,
        help="Ending timestamp (in milliseconds)"
    )
    
    # view-operations-by-path command (NEW)
    view_ops_parser = subparsers.add_parser(
        "view-operations-by-path",
        help="View all operations that start with a specific path across all patches"
    )
    view_ops_parser.add_argument(
        "path_prefix",
        help="Path prefix to filter by (e.g., 'states/map_state')"
    )
    view_ops_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of operations to display (default: 50)"
    )
    view_ops_parser.add_argument(
        "--forward-only",
        action="store_true",
        help="Only include operations from forward patches"
    )
    
    # operations-overview command (NEW)
    overview_parser = subparsers.add_parser(
        "operations-overview",
        help="Show overview of operations grouped by state"
    )
    overview_parser.add_argument(
        "--forward-only",
        action="store_true",
        help="Only analyze operations from forward patches"
    )
    
    # count-operations command
    subparsers.add_parser(
        "count-operations",
        help="Count total number of operations across all patches"
    )
    
    # count-operations-by-path command
    count_by_path_parser = subparsers.add_parser(
        "count-operations-by-path",
        help="Count operations that start with a specific path"
    )
    count_by_path_parser.add_argument(
        "path_prefix",
        help="Path prefix to filter by (e.g., 'states/map_state')"
    )
    count_by_path_parser.add_argument(
        "--forward-only",
        action="store_true",
        help="Only count operations from forward patches"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create CLI instance
    cli = ReplayDebugCLI(args.replay_file)
    
    # Open the replay
    if not cli.open_replay():
        return 1
    
    try:
        # Execute the requested command
        if args.command == "list-patches":
            cli.list_patches()
        elif args.command == "view-patch":
            cli.view_patch(args.from_timestamp, args.to_timestamp)
        elif args.command == "view-operations-by-path":
            forward_only = getattr(args, 'forward_only', False)
            cli.view_operations_by_path(args.path_prefix, args.limit, forward_only)
        elif args.command == "operations-overview":
            forward_only = getattr(args, 'forward_only', False)
            cli.operations_overview(forward_only)
        elif args.command == "count-operations":
            cli.count_operations()
        elif args.command == "count-operations-by-path":
            forward_only = getattr(args, 'forward_only', False)
            cli.count_operations_by_path(args.path_prefix, forward_only)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    finally:
        cli.close_replay()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
