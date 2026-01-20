from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class Relation(GameObject):
    C = "ultshared.diplomacy.UltRelation"
    relation: int
    color: str # TODO: Implement color class
    name: str
    description: str
    army_color: Optional[str]

    MAPPING = {
        "relation": "relation",
        "color": "color",
        "name": "name",
        "description": "desc",
        "army_color": "armyColor"
    }