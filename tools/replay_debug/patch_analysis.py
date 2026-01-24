"""
Patch analysis functionality for the Replay Debug CLI Tool.

This module provides methods for analyzing patches in replay files:
- Listing patches
- Viewing patch details and operations
- Counting and filtering operations by path
- Operations overview
"""
from typing import List, Tuple, Optional

from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import ReplayPatch
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
from tools.replay_debug.constants import SEPARATOR_WIDTH_COMPACT
from tools.replay_debug.constants import DEFAULT_LIMIT
from tools.replay_debug.formatters import format_operation_path
from tools.replay_debug.formatters import format_patch_label
from tools.replay_debug.formatters import format_timestamp
from tools.replay_debug.formatters import print_operation_row
from tools.replay_debug.formatters import print_operations_header
from tools.replay_debug.formatters import print_overview_header
from tools.replay_debug.formatters import print_overview_row
from tools.replay_debug.formatters import print_separator
from tools.replay_debug.formatters import print_patch_list_header, print_patch_list_row
from tools.replay_debug.formatters import truncate_string


class PatchAnalysisMixin:
    """Mixin providing patch analysis methods for ReplayDebugCLI."""
    
    def _load_all_patches(self):
        """Load all patches from the storage into memory."""
        # Read all patches directly from the patch graph storage (as PatchGraphNode objects)
        patches_dict = self.replay.storage.patch_graph.patches
        
        for (from_ts, to_ts), patch_node in patches_dict.items():
            # Store the native PatchGraphNode directly (no conversion needed)
            self.all_patches.append((from_ts, to_ts, patch_node))
        
        # Sort by from_timestamp, then to_timestamp
        self.all_patches.sort(key=lambda x: (x[0], x[1]))
    
    def _convert_patch_node_to_replay_patch(self, patch_node, path_tree) -> BidirectionalReplayPatch:
        """Convert a PatchGraphNode to a ReplayPatch object.
        
        This is kept for compatibility but is now only used when converting
        is explicitly needed (e.g., for detailed inspection).
        
        Args:
            patch_node: PatchGraphNode containing compressed patch data
            path_tree: PathTree for resolving path indices to actual paths
            
        Returns:
            ReplayPatch object with operations
        """
        replay_patch = BidirectionalReplayPatch()
        idx_to_node = path_tree.idx_to_node
        
        for op_type, path_idx, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
            # Reconstruct the path from the path tree
            path = self._get_path_from_index(path_idx, idx_to_node)
            
            # Create the appropriate operation
            if op_type == ADD_OPERATION:
                replay_patch.add(path, value)
            elif op_type == REPLACE_OPERATION:
                replay_patch.replace(path, None, value)
            elif op_type == REMOVE_OPERATION:
                replay_patch.remove(path, None)
            else:
                raise ValueError(f"Unknown operation type: {op_type}")

        
        return replay_patch
    
    def _get_patch_operation_count(self, patch_node):
        """Get the number of operations in a PatchGraphNode.
        
        Args:
            patch_node: PatchGraphNode object
            
        Returns:
            Number of operations in the patch
        """
        return len(patch_node.op_types)
    
    def _get_operation_type_string(self, op_type):
        """Convert operation type constant to string.
        
        Args:
            op_type: Operation type constant (ADD_OPERATION, etc.)
            
        Returns:
            String representation ('a', 'p', or 'r')
        """
        if op_type == ADD_OPERATION:
            return 'a'
        elif op_type == REPLACE_OPERATION:
            return 'p'
        elif op_type == REMOVE_OPERATION:
            return 'r'
        else:
            return '?'
    
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
        
        for i, (from_ts, to_ts, patch_node) in enumerate(self.all_patches):
            direction = "Forward" if to_ts > from_ts else "Backward"
            print_patch_list_row(i + 1, from_ts, to_ts, direction, self._get_patch_operation_count(patch_node))
    
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
    
    def _display_patch_details(self, from_timestamp: int, to_timestamp: int, patch_node, limit: int = None):
        """Display details of a PatchGraphNode interactively.
        
        Args:
            from_timestamp: Starting timestamp
            to_timestamp: Ending timestamp
            patch_node: The PatchGraphNode object to display
            limit: Maximum number of operations to display (default: 20)
        """
        if limit is None:
            limit = 20
            
        direction = "Forward" if to_timestamp > from_timestamp else "Backward"
        
        # Find the corresponding opposite direction patch for getting old values
        opposite_patch_node = None
        for from_ts, to_ts, p in self.all_patches:
            # Find the patch going the opposite direction between same timestamps
            if from_ts == to_timestamp and to_ts == from_timestamp:
                opposite_patch_node = p
                break
        
        # Get path tree and idx_to_node for path resolution
        path_tree = self.replay.storage.path_tree
        idx_to_node = path_tree.idx_to_node
        
        print(f"\n{'='*120}")
        print(f"Patch Node: {from_timestamp} -> {to_timestamp} ({direction})")
        print(f"{'='*120}")
        print(f"From: {format_timestamp(from_timestamp)}")
        print(f"To:   {format_timestamp(to_timestamp)}")
        print(f"Total operations: {len(patch_node.op_types)}")
        print(f"Cost: {patch_node.cost}")
        print("\nOperations by type:")
        print("-" * 80)
        
        # Count by type
        type_counts = {ADD_OPERATION: 0, REPLACE_OPERATION: 0, REMOVE_OPERATION: 0}
        for op_type in patch_node.op_types:
            type_counts[op_type] += 1
        
        print(f"  Add (a):     {type_counts[ADD_OPERATION]}")
        print(f"  Replace (p): {type_counts[REPLACE_OPERATION]}")
        print(f"  Remove (r):  {type_counts[REMOVE_OPERATION]}")
        
        # Build a map of opposite patch operations by path index for quick lookup
        opposite_ops = {}
        if opposite_patch_node:
            for op_type, path_idx, value in zip(opposite_patch_node.op_types, 
                                                  opposite_patch_node.paths, 
                                                  opposite_patch_node.values):
                opposite_ops[path_idx] = (op_type, value)
        
        print(f"\n{'-'*120}")
        print(f"Showing first {min(limit, len(patch_node.op_types))} operations:")
        print(f"{'-'*120}")
        print(f"{'#':>4}  {'Type':<7}  {'Path Idx':<9}  {'Path':<35}  {'Before':<22}  {'After':<22}")
        print(f"{'-'*120}")
        
        # Display operations with interactive path resolution
        operations = list(zip(patch_node.op_types, patch_node.paths, patch_node.values))
        for i, (op_type, path_idx, value) in enumerate(operations[:limit]):
            # Resolve the path
            path = self._get_path_from_index(path_idx, idx_to_node)
            path_str = format_operation_path(path)
            if len(path_str) > 35:
                path_str = path_str[:32] + "..."
            
            # Get operation type string
            op_type_str = self._get_operation_type_string(op_type)
            
            # Determine before and after values
            before_str = ""
            after_str = ""
            
            if op_type == ADD_OPERATION:
                before_str = "<not set>"
                after_str = str(value)
                # Check opposite for old value
                if path_idx in opposite_ops and opposite_ops[path_idx][0] == REMOVE_OPERATION:
                    pass  # Remove operations don't have values
            elif op_type == REPLACE_OPERATION:
                after_str = str(value)
                # Look for the opposite replace to get the old value
                if path_idx in opposite_ops and opposite_ops[path_idx][0] == REPLACE_OPERATION:
                    before_str = str(opposite_ops[path_idx][1])
                else:
                    before_str = "<unknown>"
            elif op_type == REMOVE_OPERATION:
                before_str = "<unknown>"
                after_str = "<removed>"
                # Check opposite for old value
                if path_idx in opposite_ops and opposite_ops[path_idx][0] == ADD_OPERATION:
                    before_str = str(opposite_ops[path_idx][1])
            
            # Truncate values for display
            if len(before_str) > 22:
                before_str = before_str[:19] + "..."
            if len(after_str) > 22:
                after_str = after_str[:19] + "..."
                
            print(f"{i+1:4d}. {op_type_str:<7}  {path_idx:<9}  {path_str:<35}  {before_str:<22}  {after_str:<22}")
        
        if len(patch_node.op_types) > limit:
            print(f"{'-'*120}")
            print(f"... and {len(patch_node.op_types) - limit} more operations (use --limit to see more)")
        
        print(f"{'='*120}\n")
    
    def view_operations_by_path(self, path_prefix: str, limit: int = DEFAULT_LIMIT, 
                                  direction: str = DEFAULT_DIRECTION, full_width: bool = False):
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
        idx_to_node = self.replay.storage.path_tree.idx_to_node
        
        for i, (from_ts, to_ts, patch_node) in enumerate(self.all_patches):
            is_forward = to_ts > from_ts
            
            # Apply direction filter
            if direction == 'forward' and not is_forward:
                continue
            elif direction == 'backward' and is_forward:
                continue
                
            direction_label = "Forward" if is_forward else "Backward"
            patch_index = i + 1  # 1-based index
            
            # Iterate through operations in the patch node
            for op_type, path_idx, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
                # Resolve the path
                path = self._get_path_from_index(path_idx, idx_to_node)
                
                if self._path_starts_with(path, path_parts):
                    matching_operations.append({
                        'from_ts': from_ts,
                        'to_ts': to_ts,
                        'patch_index': patch_index,
                        'direction': direction_label,
                        'op_type': op_type,
                        'path': path,
                        'path_idx': path_idx,
                        'value': value
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
            path_str = format_operation_path(match['path'])
            value_str = str(match['value'])
            op_type_str = self._get_operation_type_string(match['op_type'])
            
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
                              op_type_str, path_str, value_str, full_width)
        
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
        
        for from_ts, to_ts, patch_node in self.all_patches:
            ops_count = self._get_patch_operation_count(patch_node)
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
        
        idx_to_node = self.replay.storage.path_tree.idx_to_node
        
        for from_ts, to_ts, patch_node in self.all_patches:
            is_forward = to_ts > from_ts
            
            # Apply direction filter
            if direction == 'forward' and not is_forward:
                continue
            elif direction == 'backward' and is_forward:
                continue
                
            for op_type, path_idx, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
                total_operations += 1
                # Resolve path and check if it starts with the given prefix
                path = self._get_path_from_index(path_idx, idx_to_node)
                if self._path_starts_with(path, path_parts):
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
        idx_to_node = self.replay.storage.path_tree.idx_to_node
        
        for from_ts, to_ts, patch_node in self.all_patches:
            is_forward = to_ts > from_ts
            
            # Apply direction filter
            if direction == 'forward' and not is_forward:
                continue
            elif direction == 'backward' and is_forward:
                continue
            
            for op_type, path_idx, value in zip(patch_node.op_types, patch_node.paths, patch_node.values):
                total_ops += 1
                
                # Resolve path
                path = self._get_path_from_index(path_idx, idx_to_node)
                
                # Extract the state path (first level after 'states' or root if not under 'states')
                if len(path) > 0:
                    if path[0] == "states" and len(path) > 1:
                        state_name = f"states/{path[1]}"
                    else:
                        state_name = path[0]
                else:
                    state_name = "<root>"
                
                # Initialize state if not seen before
                op_type_str = self._get_operation_type_string(op_type)
                if state_name not in state_stats:
                    state_stats[state_name] = {'a': 0, 'p': 0, 'r': 0}
                
                # Count operation by type
                state_stats[state_name][op_type_str] += 1
        
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
