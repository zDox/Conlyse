from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


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