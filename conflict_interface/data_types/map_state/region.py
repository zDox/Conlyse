from dataclasses import dataclass
from enum import Enum

from conflict_interface.utils import GameObject, DefaultEnumMeta

@dataclass
class Region(GameObject):
    index: int
    name: str

    MAPPING = {
        "index": "index",
        "name": "name",
    }