"""
Game state viewer for inspecting replay state at any point in time.

This module provides functionality to:
- Navigate to specific paths in the game state
- Pretty print values at those paths
- Display nested structures in a readable format
"""
from typing import Any, Optional
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.apply_replay import recur_path
from conflict_interface.data_types.game_state.game_state import GameState


class StateViewer:
    """Views and inspects game state at current replay position."""
    
    def __init__(self, replay_interface: ReplayInterface):
        """Initialize the state viewer with a replay interface.
        
        Args:
            replay_interface: The ReplayInterface instance to inspect
        """
        self.ritf = replay_interface
    
    def view_path(self, path: str, max_depth: int = 5) -> None:
        """View the value at a specific path in the game state.
        
        Args:
            path: Path to the value (e.g., "states/map_state/provinces/0")
            max_depth: Maximum depth for nested structure display
        """
        if not self.ritf.game_state:
            print("Error: Game state not loaded")
            return
        
        # Parse the path
        path_parts = path.split("/") if path else []
        
        if not path_parts:
            print("Error: Path is empty")
            return
        
        try:
            # Use recur_path to navigate to the location
            parent_obj, final_key, value_type = recur_path(
                self.ritf.game_state,
                GameState,
                path_parts.copy(),
                self.ritf.game_state,
                self.ritf
            )
            
            # Get the value
            if isinstance(parent_obj, dict):
                value = parent_obj.get(final_key)
            elif isinstance(parent_obj, list):
                value = parent_obj[int(final_key)]
            else:
                value = getattr(parent_obj, final_key)
            
            # Display the value
            print(f"\nPath: {path}")
            print(f"Type: {type(value).__name__}")
            print(f"Value Type Hint: {value_type}")
            print("-" * 80)
            
            self._pretty_print_value(value, max_depth=max_depth)
            
        except (ValueError, AttributeError, KeyError, IndexError) as e:
            print(f"Error accessing path '{path}': {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    def _pretty_print_value(self, value: Any, indent: int = 0, max_depth: int = 5, current_depth: int = 0) -> None:
        """Pretty print a value with proper formatting.
        
        Args:
            value: The value to print
            indent: Current indentation level
            max_depth: Maximum depth to recurse
            current_depth: Current recursion depth
        """
        indent_str = "  " * indent
        
        # Handle depth limit
        if current_depth >= max_depth:
            print(f"{indent_str}... (max depth reached)")
            return
        
        # Handle None
        if value is None:
            print(f"{indent_str}None")
            return
        
        # Handle basic types
        if isinstance(value, (str, int, float, bool)):
            print(f"{indent_str}{value}")
            return
        
        # Handle lists
        if isinstance(value, list):
            if not value:
                print(f"{indent_str}[]")
                return
            
            print(f"{indent_str}[")
            # Limit to first 20 items for very long lists
            items_to_show = min(len(value), 20)
            for i, item in enumerate(value[:items_to_show]):
                if isinstance(item, (dict, list)) or hasattr(item, '__dict__'):
                    print(f"{indent_str}  [{i}]:")
                    self._pretty_print_value(item, indent + 2, max_depth, current_depth + 1)
                else:
                    print(f"{indent_str}  [{i}]: {item}")
            
            if len(value) > items_to_show:
                print(f"{indent_str}  ... and {len(value) - items_to_show} more items")
            print(f"{indent_str}]")
            return
        
        # Handle dicts
        if isinstance(value, dict):
            if not value:
                print(f"{indent_str}{{}}")
                return
            
            print(f"{indent_str}{{")
            # Limit to first 20 keys for very large dicts
            keys_to_show = list(value.keys())[:20]
            for key in keys_to_show:
                item = value[key]
                if isinstance(item, (dict, list)) or hasattr(item, '__dict__'):
                    print(f"{indent_str}  {key}:")
                    self._pretty_print_value(item, indent + 2, max_depth, current_depth + 1)
                else:
                    print(f"{indent_str}  {key}: {item}")
            
            if len(value) > len(keys_to_show):
                print(f"{indent_str}  ... and {len(value) - len(keys_to_show)} more keys")
            print(f"{indent_str}}}")
            return
        
        # Handle GameObject and other objects with __dict__
        if hasattr(value, '__dict__'):
            obj_dict = value.__dict__
            if not obj_dict:
                print(f"{indent_str}{type(value).__name__}()")
                return
            
            print(f"{indent_str}{type(value).__name__}(")
            # Limit to first 20 attributes
            attrs_to_show = list(obj_dict.keys())[:20]
            for attr_name in attrs_to_show:
                attr_value = obj_dict[attr_name]
                if isinstance(attr_value, (dict, list)) or hasattr(attr_value, '__dict__'):
                    print(f"{indent_str}  {attr_name}:")
                    self._pretty_print_value(attr_value, indent + 2, max_depth, current_depth + 1)
                else:
                    print(f"{indent_str}  {attr_name}: {attr_value}")
            
            if len(obj_dict) > len(attrs_to_show):
                print(f"{indent_str}  ... and {len(obj_dict) - len(attrs_to_show)} more attributes")
            print(f"{indent_str})")
            return
        
        # Fallback for unknown types
        try:
            print(f"{indent_str}{repr(value)}")
        except Exception:
            print(f"{indent_str}<{type(value).__name__} object>")
    
    def list_available_states(self) -> None:
        """List the main state categories available in the game state."""
        if not self.ritf.game_state:
            print("Error: Game state not loaded")
            return
        
        print("\nAvailable state categories:")
        print("-" * 80)
        
        if hasattr(self.ritf.game_state, 'states'):
            states_obj = self.ritf.game_state.states
            if hasattr(states_obj, '__dict__'):
                for attr_name in sorted(states_obj.__dict__.keys()):
                    attr_value = getattr(states_obj, attr_name)
                    print(f"  states/{attr_name} - {type(attr_value).__name__}")
        
        # Show other top-level attributes
        print("\nOther game state attributes:")
        for attr_name in sorted(self.ritf.game_state.__dict__.keys()):
            if attr_name != 'states':
                attr_value = getattr(self.ritf.game_state, attr_name)
                print(f"  {attr_name} - {type(attr_value).__name__}")
    
    def search_path(self, search_term: str) -> None:
        """Search for attributes containing a search term.
        
        Args:
            search_term: Term to search for in attribute names
        """
        if not self.ritf.game_state:
            print("Error: Game state not loaded")
            return
        
        search_term_lower = search_term.lower()
        matches = []
        
        def search_recursive(obj: Any, path: str, depth: int = 0):
            """Recursively search for matching paths."""
            if depth > 3:  # Limit search depth
                return
            
            if hasattr(obj, '__dict__'):
                for attr_name in obj.__dict__.keys():
                    if search_term_lower in attr_name.lower():
                        matches.append(f"{path}/{attr_name}")
                    
                    # Recurse into nested objects
                    try:
                        attr_value = getattr(obj, attr_name)
                        if hasattr(attr_value, '__dict__'):
                            search_recursive(attr_value, f"{path}/{attr_name}", depth + 1)
                    except Exception:
                        pass
        
        search_recursive(self.ritf.game_state, "", 0)
        
        print(f"\nFound {len(matches)} paths containing '{search_term}':")
        print("-" * 80)
        for match in sorted(matches[:50]):  # Limit to 50 results
            print(f"  {match.lstrip('/')}")
        
        if len(matches) > 50:
            print(f"\n... and {len(matches) - 50} more matches")
