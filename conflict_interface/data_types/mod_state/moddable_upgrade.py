from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable
from conflict_interface.data_types.point import Point

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class ModableUpgrade(GameObject):
    id: int
    condition: Optional[int]

    relative_position: Optional[Point]
    built: bool = False
    enabled: bool = True
    premium_level: int = 0
    constructing: bool = False
    C = "mu"
    MAPPING = {
        "id": "id",
        "condition": "c",
        "constructing": "cn",
        "enabled": "e",
        "relative_position": "rp",
        "premium_level": "pl",
        "built": "built",
    }

    __hash__ = GameObject.__hash__