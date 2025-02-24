from dataclasses import dataclass
from enum import Enum

from conflict_interface.utils import GameObject, DefaultEnumMeta

@dataclass
class Region(GameObject):
    """
    Represents a region on the map. For example Africa and Europe are regions.
    """
    index: int
    name: str

    MAPPING = {
        "index": "index",
        "name": "name",
    }