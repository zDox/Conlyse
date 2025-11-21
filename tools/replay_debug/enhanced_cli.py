"""
Enhanced CLI class with ReplayInterface integration.

This module provides an enhanced version of the CLI that integrates
with ReplayInterface for live game state inspection and navigation.
"""
from typing import Optional
from conflict_interface.interface.replay_interface import ReplayInterface
from .navigation import ReplayNavigator
from .state_viewer import StateViewer


class EnhancedReplayDebugCLI:
    """Enhanced CLI with ReplayInterface integration for live state inspection."""
    
    def __init__(self, filename: str):
        """Initialize the enhanced CLI with a replay file.
        
        Args:
            filename: Path to the replay database file
        """
        self.filename = filename
        self.ritf: Optional[ReplayInterface] = None
        self.navigator: Optional[ReplayNavigator] = None
        self.state_viewer: Optional[StateViewer] = None
    
    def open_replay(self) -> bool:
        """Open the replay file with ReplayInterface.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ritf = ReplayInterface(self.filename)
            self.ritf.open()
            self.navigator = ReplayNavigator(self.ritf)
            self.state_viewer = StateViewer(self.ritf)
            return True
        except FileNotFoundError:
            print(f"Error: Replay file '{self.filename}' not found.")
            return False
        except Exception as e:
            print(f"Error opening replay: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def close_replay(self):
        """Close the replay file."""
        if self.ritf:
            self.ritf.close()
    
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
        
        try:
            from dateutil import parser
            timestamp = parser.parse(timestamp_str)
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
    
    def list_timestamps(self, limit: int = 50):
        """List timestamps."""
        if not self.navigator:
            print("Error: Replay not opened.")
            return
        
        self.navigator.list_timestamps(limit)
    
    # State viewing methods
    def view_state_path(self, path: str, max_depth: int = 5):
        """View value at a path in the game state."""
        if not self.state_viewer:
            print("Error: Replay not opened.")
            return
        
        self.state_viewer.view_path(path, max_depth)
    
    def list_states(self):
        """List available state categories."""
        if not self.state_viewer:
            print("Error: Replay not opened.")
            return
        
        self.state_viewer.list_available_states()
    
    def search_paths(self, search_term: str):
        """Search for paths containing a term."""
        if not self.state_viewer:
            print("Error: Replay not opened.")
            return
        
        self.state_viewer.search_path(search_term)
    
    # Direct access to RITF
    def get_ritf(self) -> Optional[ReplayInterface]:
        """Get the ReplayInterface instance for advanced usage.
        
        Returns:
            The ReplayInterface instance or None if not opened
        """
        return self.ritf
