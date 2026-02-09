from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from typing import TYPE_CHECKING

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.data_types.point import Point

if TYPE_CHECKING:
    from conflict_interface.data_types.mod_state.upgrade_type import UpgradeType

@conflict_serializable(SerializationCategory.DATACLASS)
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

    def get_upgrade_type(self) -> UpgradeType:
        return self.game.get_upgrade_type(self.id)