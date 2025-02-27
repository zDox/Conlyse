from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class Region(GameObject):
    """
    Represents a region on the map. For example Africa and Europe are regions.
    """
    C = "ultshared.UltRegion"
    index: int
    name: str

    MAPPING = {
        "index": "index",
        "name": "name",
    }