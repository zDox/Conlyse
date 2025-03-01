from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject


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