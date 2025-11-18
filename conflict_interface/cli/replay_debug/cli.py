"""
Main CLI class for the Replay Debug Tool.
"""
from typing import Optional, List, Tuple
from datetime import datetime, UTC

from conflict_interface.replay.replay import Replay
from conflict_interface.replay.replay_patch import ReplayPatch

from .constants import *
from .formatters import *


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
        print_separator(SEPARATOR_WIDTH_COMPACT)
        print_patch_list_header()
        
        for i, (from_ts, to_ts, patch) in enumerate(self.all_patches):
            direction = "Forward" if to_ts > from_ts else "Backward"
            print_patch_list_row(i + 1, from_ts, to_ts, direction, len(patch.operations))
    
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
        print(f"From: {format_timestamp(from_timestamp)}")
        print(f"To:   {format_timestamp(to_timestamp)}")
        print(f"Total operations: {len(patch.operations)}")
        print("\nOperations by type:")
        print("-" * 80)
        
        # Count by type
        type_counts = {'a': 0, 'p': 0, 'r': 0}
        for op in patch.operations:
            type_counts[op.Key] += 1
        
        print(f"  Add:     {type_counts['a']}")
        print(f"  Replace: {type_counts['p']}")
        print(f"  Remove:  {type_counts['r']}")
        
        print("\nFirst 20 operations:")
        print("-" * 80)
        for i, op in enumerate(patch.operations[:20]):
            path_str = format_operation_path(op.path)
            value_str = str(op.new_value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            print(f"{i+1:4d}. {op.Key:7s} {path_str:40s} -> {value_str}")
        
        if len(patch.operations) > 20:
            print(f"\n... and {len(patch.operations) - 20} more operations")
    
    def _get_patch_index(self, from_ts: int, to_ts: int) -> int:
        """Get the 1-based index of a patch.
        
        Args:
            from_ts: Starting timestamp
            to_ts: Ending timestamp
            
        Returns:
            1-based index, or 0 if not found
        """
        for i, (f_ts, t_ts, _) in enumerate(self.all_patches):
            if f_ts == from_ts and t_ts == to_ts:
                return i + 1
        return 0
    
    def view_operations_by_path(self, path_prefix: str, limit: int = DEFAULT_LIMIT, direction: str = DEFAULT_DIRECTION, full_width: bool = False):
        """View all operations that start with a specific path across all patches.
        
        Args:
            path_prefix: Path to filter by
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
        for i, (from_ts, to_ts, patch) in enumerate(self.all_patches):
            is_forward = to_ts > from_ts
            
            # Apply direction filter
            if direction == 'forward' and not is_forward:
                continue
            elif direction == 'backward' and is_forward:
                continue
                
            direction_label = "Forward" if is_forward else "Backward"
            patch_index = i + 1  # 1-based index
            
            for op in patch.operations:
                if self._path_starts_with(op.path, path_parts):
                    matching_operations.append({
                        'from_ts': from_ts,
                        'to_ts': to_ts,
                        'patch_index': patch_index,
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
        
        print_operations_header(full_width)
        
        for i, match in enumerate(matching_operations[:limit]):
            op = match['operation']
            path_str = format_operation_path(op.path)
            value_str = str(op.new_value)
            
            patch_label = format_patch_label(match['from_ts'], match['to_ts'], 
                                            COLUMN_WIDTH_PATCH_FULL if full_width else COLUMN_WIDTH_PATCH)
            
            if full_width:
                # For full width, still limit path for readability, but show full value
                path_str = truncate_string(path_str, COLUMN_WIDTH_PATH_FULL)
            else:
                # Compact output with truncation
                path_str = truncate_string(path_str, COLUMN_WIDTH_PATH_COMPACT)
                value_str = truncate_string(value_str, COLUMN_WIDTH_VALUE_COMPACT)
            
            print_operation_row(i + 1, patch_label, match['patch_index'], match['direction'], 
                              op.Key, path_str, value_str, full_width)
        
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
    
    def count_operations_by_path(self, path_prefix: str, direction: str = DEFAULT_DIRECTION):
        """Count operations that start with a specific path.
        
        Args:
            path_prefix: Path prefix to filter by
            direction: Direction filter - 'both', 'forward', or 'backward' (default: DEFAULT_DIRECTION)
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
    
    def operations_overview(self, direction: str = DEFAULT_DIRECTION):
        """Show overview of operations grouped by state.
        
        Args:
            direction: Direction filter - 'both', 'forward', or 'backward' (default: DEFAULT_DIRECTION)
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
        print_overview_header()
        
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
            
            print_overview_row(state_name, add_count, replace_count, remove_count, total_count)
        
        print_separator(SEPARATOR_WIDTH_OVERVIEW)
        
        # Summary totals
        total_add = sum(counts['a'] for counts in state_stats.values())
        total_replace = sum(counts['p'] for counts in state_stats.values())
        total_remove = sum(counts['r'] for counts in state_stats.values())
        
        print_overview_row("TOTAL", total_add, total_replace, total_remove, total_ops)
    
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
