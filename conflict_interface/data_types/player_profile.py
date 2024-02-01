from dataclasses import dataclass
from enum import Enum

from conflict_interface.utils import JsonMappedClass, DefaultEnumMeta


class Faction(Enum, metaclass=DefaultEnumMeta):
    NONE = 0
    WESTERN = 1
    EASTERN = 2
    EUROPEAN = 3


@dataclass
class PlayerProfile(JsonMappedClass):
    id: int
    faction: Faction
    team_id: int
    name: str
    nation_name: str
    computer_player: bool
    native_computer: bool
    site_user_id: int
    defeated: bool
    retired: bool
    passive_ai: bool
    playing: bool
    taken: bool
    available: bool

    mapping = {
        "id": "playerID",
        "faction": "faction",
        "team_id": "teamID",
        "name": "name",
        "nation_name": "nationName",
        "computer_player": "computerPlayer",
        "native_computer": "nativeComputer",
        "site_user_id": "siteUserID",
        "defeated": "defeated",
        "retired": "retired",
        "passive_ai": "passiveAI",
        "playing": "playing",
        "taken": "taken",
        "available": "available",
    }
