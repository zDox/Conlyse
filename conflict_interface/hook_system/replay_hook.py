from dataclasses import dataclass
from typing import Callable

from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag


@dataclass
class ReplayHook:
    """Represents a registered hook with its pattern and callback."""
    tag: ReplayHookTag # Unique identifier for the hook
    path: int  # Path pattern with potential wildcards
    change_types: list[int]  # Which change types trigger this hook
    attributes: list[str] | None # Which attribute names to look for. If None, all attributes are matched
    callback: Callable = None # Optional callback function callback(reference, changed_data)
    search_start_depth: int = 0 # Depth in the path tree at which the system starts looking for changes depth is 0 at the hook path
    search_end_depth: int = -1 # Depth in the path tree at which the system stops looking for changes (inclusive); If -1, depth is disregarded