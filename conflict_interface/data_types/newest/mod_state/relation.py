from dataclasses import dataclass
from typing import Optional

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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