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
from tools.replay_debug.game_object_viewer import GameObjectViewer
from tools.replay_debug.navigation import ReplayNavigator
from tools.replay_debug.check_timestamps import check_timestamps
from tools.replay_debug.patch_analysis import PatchAnalysisMixin


class ReplayDebugCLI(PatchAnalysisMixin):
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
    
    def close_replay(self):
        """Close the replay file."""
        if self.ritf:
            self.ritf.close()
    
    # ===== NAVIGATION AND INFO METHODS =====
    
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
        print(f"Game Speed: {self.ritf.speed_modifier}")
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
    
    # ===== GAME OBJECT VIEWING METHODS =====
    
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

    def check_timestamps(self):
        """Check timestamps in the replay."""
        if not self.ritf:
            print("Error: Replay not opened.")
            return
        check_timestamps(self.ritf)
    
    # ===== REPLAY INTERFACE ACCESS =====
    
    def get_ritf(self) -> Optional[ReplayInterface]:
        """Get the ReplayInterface instance for advanced usage.
        
        Returns:
            The ReplayInterface instance or None if not opened
        """
        return self.ritf
