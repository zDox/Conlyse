from dataclasses import dataclass
from typing import Callable

from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag


@dataclass
class ReplayHook:
    """Represents a registered hook with its pattern and callback."""
    tag: ReplayHookTag # Unique identifier for the hook
    path: int  # Path pattern with potential wildcards
    change_types: list[int]  # Which change types trigger this hook
    attributes: list[str] # Which attribute names to look for
    callback: Callable = None # Optional callback function callback(reference, changed_data)