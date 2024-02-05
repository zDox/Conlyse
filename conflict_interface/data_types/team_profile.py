from conflict_interface.utils import JsonMappedClass

from dataclasses import dataclass


"""
Not implemented
getPrimaryColor
getInGameAlliance
getFlagImageURL
getFlagImageID
getFlagImageTag
getFlagImage
"""


@dataclass
class TeamProfile(JsonMappedClass):
    id: int
    name: str
    description: str
    leader_id: int
    disbanded: bool
    victory_points: int

    mapping = {
            "id": "id",
            "name": "name",
            "description": "description",
            "leader_id": "leaderID",
            "disbanded": "disbanded",
            "victory_points": "vps",
    }

    def get_team_id(self):
        return self.id

    def get_team_name(self):
        return self.name

    def get_description(self):
        return self.description

    def get_leader_id(self):
        return self.leader_id

    def is_disbanded(self):
        return self.disbanded

    def get_victory_points(self):
        return self.victory_points
