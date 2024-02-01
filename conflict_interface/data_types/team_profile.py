from conflict_interface.utils import JsonMappedClass

from dataclasses import dataclass


@dataclass
class TeamProfile(JsonMappedClass):
    id: int
    name: str
    description: str
    leader_id: int
    disbanded: bool

    mapping = {
            "id": "id",
            "name": "name",
            "description": "description",
            "leader_id": "leaderID",
            "disbanded": "disbanded",
    }
