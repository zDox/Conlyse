from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject


@dataclass
class SpyMission(GameObject):
    C = "ultshared.spyjobs.UltSpyMission"
    mission_type: int
    name: str
    help_text: Optional[str]
    daily_cost: Optional[int]
    friendly: bool
    hostile: bool
    icon_name: Optional[str]
    help_title: Optional[str]
    color: str # TODO implement color type
    help_icon: Optional[str]

    MAPPING = {
        "mission_type": "missionType",
        "name": "name",
        "help_text": "helpText",
        "daily_cost": "dailyCosts",
        "friendly": "friendly",
        "hostile": "hostile",
        "icon_name": "iconName",
        "help_title": "helpTitle",
        "color": "color",
        "help_icon": "helpIcon"
    }

