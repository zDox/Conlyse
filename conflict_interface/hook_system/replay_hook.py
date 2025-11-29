from dataclasses import dataclass
from typing import Callable


@dataclass
class ReplayHook:
    """Represents a registered hook with its pattern and callback."""
    path: int  # Path pattern with potential wildcards
    change_types: list[int]  # Which change types trigger this hook
    attributes: list[str] # Which attribute names to look for
    callback: Callable = None # Optional callback function callback(reference, changed_data)