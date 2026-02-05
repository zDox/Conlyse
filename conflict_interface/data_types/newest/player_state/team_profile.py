from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
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

    def is_disbanded(self):
        return self.disbanded
