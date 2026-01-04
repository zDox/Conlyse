"""
CLI class for the Replay Debug Tool.

This module provides a CLI that combines patch analysis with
live game state inspection and navigation via ReplayInterface.
"""
from typing import List
from typing import Optional
from typing import Tuple

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.replay_patch import ReplayPatch
from tools.replay_debug.game_object_viewer import GameObjectViewer
from tools.replay_debug.navigation import ReplayNavigator
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
            self.ritf.open(mode="r")
            self.navigator = ReplayNavigator(self.ritf)
            self.game_object_viewer = GameObjectViewer(self.ritf)
            # Set replay reference for patch analysis methods
            self.replay = self.ritf._replay
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
