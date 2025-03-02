from typing import Optional

from conflict_interface.data_types.game_object import GameObject

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
class TeamProfile(GameObject):
    C = "ultshared.UltTeamProfile"
    team_id: int
    name: str
    description: str
    leader_id: int
    disbanded: bool

    primary_color: str  # TODO implement Color
    accumulated_victory_points: int
    daily_victory_points: int

    flag_image_id: int = -1
    victory_points: int = 0

    MAPPING = {
        "team_id": "teamID",
        "name": "name",
        "description": "description",
        "leader_id": "leaderID",
        "disbanded": "disbanded",
        "victory_points": "vps",
        "primary_color": "primaryColor",
        "flag_image_id": "flagImageID",
        "accumulated_victory_points": "accumulatedVps",
        "daily_victory_points": "dailyVictoryPoints",
    }

    def get_team_id(self):
        return self.team_id

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
