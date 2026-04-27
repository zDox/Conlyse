from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class AggressionLevel(GameObject):
    C = "ultshared.warfare.UltAggressionLevel"
    level: int
    name: str
    description: str

    MAPPING = {
        "level": "level",
        "name": "name",
        "description": "desc"
    }