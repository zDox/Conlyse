from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class Region(GameObject):
    """
    Represents a region on the map. For example Africa and Europe are regions.
    """
    C = "ultshared.map.UltRegion"
    index: int
    name: str

    MAPPING = {
        "index": "index",
        "name": "name",
    }