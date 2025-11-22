"""
CLI class for the Replay Debug Tool.

This module provides a CLI that combines patch analysis with
live game state inspection and navigation via ReplayInterface.
"""
from typing import List
from typing import Optional
from typing import Tuple

from dateutil import parser as dateparser

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.replay_patch import ReplayPatch
from conflict_interface.replay.replay_patch import AddOperation
from conflict_interface.replay.replay_patch import ReplaceOperation
from conflict_interface.replay.replay_patch import RemoveOperation
from conflict_interface.replay.constants import ADD_OPERATION
from conflict_interface.replay.constants import REPLACE_OPERATION
from conflict_interface.replay.constants import REMOVE_OPERATION
from tools.replay_debug.constants import COLUMN_WIDTH_PATCH
from tools.replay_debug.constants import COLUMN_WIDTH_PATCH_FULL
from tools.replay_debug.constants import COLUMN_WIDTH_PATH_COMPACT
from tools.replay_debug.constants import COLUMN_WIDTH_PATH_FULL
from tools.replay_debug.constants import COLUMN_WIDTH_VALUE_COMPACT
from tools.replay_debug.constants import DEFAULT_DIRECTION
from tools.replay_debug.constants import SEPARATOR_WIDTH_OVERVIEW
from tools.replay_debug.constants import DEFAULT_LIMIT
from tools.replay_debug.formatters import format_operation_path
from tools.replay_debug.formatters import format_patch_label
from tools.replay_debug.formatters import format_timestamp
from tools.replay_debug.formatters import print_operation_row
from tools.replay_debug.formatters import print_operations_header
from tools.replay_debug.formatters import print_overview_header
from tools.replay_debug.formatters import print_overview_row
from tools.replay_debug.formatters import print_separator, SEPARATOR_WIDTH_COMPACT, print_patch_list_header, print_patch_list_row
from tools.replay_debug.formatters import truncate_string
from tools.replay_debug.game_object_viewer import GameObjectViewer
from tools.replay_debug.navigation import ReplayNavigator


class ReplayDebugCLI:
    """CLI for debugging replay files with navigation and patch analysis."""
    
    def __init__(self, filename: str):
        """Initialize the CLI with a replay file.
        
        Args:
            filename: Path to the replay database file
        """
        self.filename = filename
        self.ritf: Optional[ReplayInterface] = None
        self.navigator: Optional[ReplayNavigator] = None
        self.game_object_viewer: Optional[GameObjectViewer] = None
        self.all_patches: List[Tuple[int, int, ReplayPatch]] = []
        self.replay = None
    
    def open_replay(self) -> bool:
        """Open the replay file with ReplayInterface.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ritf = ReplayInterface(self.filename)
            self.ritf.open()
            self.navigator = ReplayNavigator(self.ritf)
            self.game_object_viewer = GameObjectViewer(self.ritf)
            # Set replay reference for patch analysis methods
            self.replay = self.ritf.replay
            # Load all patches into memory for patch analysis
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
        """Load all patches from the storage into memory."""
        # Read all patches from the patch graph storage
        patches_dict = self.replay.storage.patch_graph.patches
        path_tree = self.replay.storage.path_tree
        
        for (from_ts, to_ts), patch_node in patches_dict.items():
            # Convert PatchGraphNode to ReplayPatch
            replay_patch = self._convert_patch_node_to_replay_patch(patch_node, path_tree)
            self.all_patches.append((from_ts, to_ts, replay_patch))
        
        # Sort by from_timestamp, then to_timestamp
        self.all_patches.sort(key=lambda x: (x[0], x[1]))
    
    def _convert_patch_node_to_replay_patch(self, patch_node, path_tree):
        """Convert a PatchGraphNode to a ReplayPatch object.
        
        Args:
            patch_node: PatchGraphNode containing compressed patch data
            path_tree: PathTree for resolving path indices to actual paths
            
        Returns:
            ReplayPatch object with operations
        """
        replay_patch = ReplayPatch()
        idx_to_node = path_tree.idx_to_node
        
        for op_type, path_idx, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
            # Reconstruct the path from the path tree
            path = self._get_path_from_index(path_idx, idx_to_node)
            
            # Create the appropriate operation
            if op_type == ADD_OPERATION:
                op = AddOperation(path=path, new_value=value)
            elif op_type == REPLACE_OPERATION:
                op = ReplaceOperation(path=path, new_value=value)
            elif op_type == REMOVE_OPERATION:
                op = RemoveOperation(path=path)
            else:
                raise ValueError(f"Unknown operation type: {op_type}")
            
            replay_patch.operations.append(op)
        
        return replay_patch
    
    def _get_path_from_index(self, path_idx, idx_to_node):
        """Reconstruct the full path from a path index.
        
        Args:
            path_idx: Index of the path node in the path tree
            idx_to_node: Dictionary mapping indices to PathNode objects
            
        Returns:
            List representing the path
        """
        path = []
        node = idx_to_node[path_idx]
        
        # Walk up the tree to the root, collecting path elements
        # Add safety check to prevent infinite loops
        visited = set()
        while node.index != 0:  # 0 is the root
            if node.index in visited:
                raise ValueError(f"Cycle detected in path tree at node {node.index}")
            visited.add(node.index)
            
            path.append(node.path_element)
            
            # Get parent node with bounds checking
            parent_array = self.replay.storage.path_tree.parent
            if node.index >= len(parent_array):
                raise ValueError(f"Node index {node.index} exceeds parent array bounds")
            
            parent_idx = parent_array[node.index]
            if parent_idx < 0 or parent_idx not in idx_to_node:
                raise ValueError(f"Invalid parent index {parent_idx} for node {node.index}")
            
            node = idx_to_node[parent_idx]
        
        # Reverse to get the path from root to target
        path.reverse()
        return path
    
    def close_replay(self):
        """Close the replay file."""
        if self.ritf:
            self.ritf.close()

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
        print(f"Start time: {self.replay.get_start_time()}")
        print(f"End time: {self.replay.get_last_time()}")
        print("\nAll patches (including forward and backward):")
        print("Note: Use 'vp <index>' to view a patch by its index number")
        print_separator(SEPARATOR_WIDTH_COMPACT)
        print_patch_list_header()
        
        for i, (from_ts, to_ts, patch) in enumerate(self.all_patches):
            direction = "Forward" if to_ts > from_ts else "Backward"
            print_patch_list_row(i + 1, from_ts, to_ts, direction, len(patch.operations))
    
    def view_patch(self, from_timestamp: int, to_timestamp: int, limit: int = None):
        """View operations in a specific patch.
        
        Args:
            from_timestamp: Starting timestamp
            to_timestamp: Ending timestamp
            limit: Maximum number of operations to display (default: None shows all)
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
        
        self._display_patch_details(from_timestamp, to_timestamp, patch, limit)
    
    def view_patch_by_index(self, index: int, limit: int = None):
        """View operations in a patch by its index from list_patches.
        
        Args:
            index: 1-based index of the patch (as shown in list_patches)
            limit: Maximum number of operations to display (default: None shows all)
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
        self._display_patch_details(from_ts, to_ts, patch, limit)
    
    def _display_patch_details(self, from_timestamp: int, to_timestamp: int, patch: ReplayPatch, limit: int = None):
        """Display details of a specific patch.
        
        Args:
            from_timestamp: Starting timestamp
            to_timestamp: Ending timestamp
            patch: The ReplayPatch object to display
            limit: Maximum number of operations to display (default: 20)
        """
        if limit is None:
            limit = 20
            
        direction = "Forward" if to_timestamp > from_timestamp else "Backward"
        
        # Find the corresponding opposite direction patch for getting old values
        opposite_patch = None
        for from_ts, to_ts, p in self.all_patches:
            # Find the patch going the opposite direction between same timestamps
            if from_ts == to_timestamp and to_ts == from_timestamp:
                opposite_patch = p
                break
        
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
        
        # Build a map of opposite patch operations by path for quick lookup
        opposite_ops = {}
        if opposite_patch:
            for op in opposite_patch.operations:
                path_key = tuple(op.path)
                opposite_ops[path_key] = op
        
        print(f"\nShowing first {min(limit, len(patch.operations))} operations:")
        print("-" * 120)
        print(f"{'#':>4}  {'Type':<7}  {'Path':<40}  {'Before':<25}  {'After':<25}")
        print("-" * 120)
        
        for i, op in enumerate(patch.operations[:limit]):
            path_str = format_operation_path(op.path)
            if len(path_str) > 40:
                path_str = path_str[:37] + "..."
            
            # Determine before and after values based on operation type
            before_str = ""
            after_str = ""
            path_key = tuple(op.path)
            
            if op.Key == 'a':  # Add operation
                before_str = "<not set>"
                after_str = str(op.new_value)
                # Check opposite for old value (should be a remove operation)
                if path_key in opposite_ops and opposite_ops[path_key].Key == 'r':
                    # Remove operations don't have a value, so we keep "<not set>"
                    pass
            elif op.Key == 'p':  # Replace operation
                after_str = str(op.new_value)
                # Look for the opposite replace to get the old value
                if path_key in opposite_ops and opposite_ops[path_key].Key == 'p':
                    before_str = str(opposite_ops[path_key].new_value)
                else:
                    before_str = "<unknown>"
            elif op.Key == 'r':  # Remove operation
                before_str = "<unknown>"
                after_str = "<removed>"
                # Check opposite for old value (should be an add operation)
                if path_key in opposite_ops and opposite_ops[path_key].Key == 'a':
                    before_str = str(opposite_ops[path_key].new_value)
            
            # Truncate values for display
            if len(before_str) > 25:
                before_str = before_str[:22] + "..."
            if len(after_str) > 25:
                after_str = after_str[:22] + "..."
                
            print(f"{i+1:4d}. {op.Key:<7}  {path_str:<40}  {before_str:<25}  {after_str:<25}")
        
        if len(patch.operations) > limit:
            print(f"\n... and {len(patch.operations) - limit} more operations (use --limit to see more)")
    
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
    
    # ===== NAVIGATION AND GAME OBJECT VIEWING METHODS =====
    def display_info(self):
        """Display current replay position and metadata."""
        if not self.ritf:
            print("Error: Replay not opened.")
            return
        
        idx, current, start, end = self.navigator.get_current_position_info()
        
        print("\nReplay Information")
        print("=" * 80)
        print(f"File:        {self.filename}")
        print(f"Game ID:     {self.ritf.game_id}")
        print(f"Player ID:   {self.ritf.player_id}")
        print(f"\nStart Time:  {start.isoformat()}")
        print(f"End Time:    {end.isoformat()}")
        print(f"Duration:    {(end - start).total_seconds():.2f} seconds")
        print(f"\nCurrent Position:")
        print(f"  Time:      {current.isoformat()}")
        print(f"  Index:     {idx}")
        print(f"  Progress:  {((current - start).total_seconds() / (end - start).total_seconds() * 100):.1f}%")
        
        # Show timestamp stats
        timestamps = self.ritf.get_timestamps()
        print(f"\nTotal Timestamps: {len(timestamps)}")
    
    # Navigation methods
    def jump_relative(self, seconds: float):
        """Jump by relative time."""
        if not self.navigator:
            print("Error: Replay not opened.")
            return
        
        if self.navigator.jump_by_relative_time(seconds):
            print(f"Jumped to: {self.ritf.current_time.isoformat()}")
        else:
            print("Failed to jump.")
    
    def jump_absolute(self, timestamp_str: str):
        """Jump to absolute time."""
        if not self.navigator:
            print("Error: Replay not opened.")
            return
        
        if not timestamp_str or not timestamp_str.strip():
            print("Error: Timestamp string cannot be empty.")
            return
        
        try:
            timestamp = dateparser.parse(timestamp_str)
            if self.navigator.jump_to_absolute_time(timestamp):
                print(f"Jumped to: {self.ritf.current_time.isoformat()}")
            else:
                print("Failed to jump.")
        except Exception as e:
            print(f"Error parsing timestamp: {e}")
    
    def jump_patches(self, num_patches: int):
        """Jump by number of patches."""
        if not self.navigator:
            print("Error: Replay not opened.")
            return
        
        if self.navigator.jump_by_patches(num_patches):
            print(f"Jumped to: {self.ritf.current_time.isoformat()}")
        else:
            print("Failed to jump.")
    
    def jump_index(self, index: int):
        """Jump to timestamp by index."""
        if not self.navigator:
            print("Error: Replay not opened.")
            return
        
        if self.navigator.jump_to_timestamp_index(index):
            print(f"Jumped to: {self.ritf.current_time.isoformat()}")
        else:
            print("Failed to jump.")
    
    def list_timestamps(self, limit: int = 50, relative: bool = False):
        """List timestamps.
        
        Args:
            limit: Maximum number of timestamps to display
            relative: If True, show times relative to current position
        """
        if not self.navigator:
            print("Error: Replay not opened.")
            return
        
        self.navigator.list_timestamps(limit, relative)
    
    # Game Object viewing methods
    def view_game_object_path(self, path: str, max_depth: int = 5):
        """View value at a path in the game state."""
        if not self.game_object_viewer:
            print("Error: Replay not opened.")
            return
        
        self.game_object_viewer.view_path(path, max_depth)
    
    def list_states(self):
        """List available state categories."""
        if not self.game_object_viewer:
            print("Error: Replay not opened.")
            return
        
        self.game_object_viewer.list_available_states()
    
    def search_paths(self, search_term: str):
        """Search for paths containing a term."""
        if not self.game_object_viewer:
            print("Error: Replay not opened.")
            return
        
        self.game_object_viewer.search_path(search_term)
    
    # Direct access to RITF
    def get_ritf(self) -> Optional[ReplayInterface]:
        """Get the ReplayInterface instance for advanced usage.
        
        Returns:
            The ReplayInterface instance or None if not opened
        """
        return self.ritf
