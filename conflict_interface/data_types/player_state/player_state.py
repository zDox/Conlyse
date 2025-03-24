from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.player_state.player_profile import PlayerProfile
from conflict_interface.data_types.player_state.team_profile import TeamProfile
from conflict_interface.data_types.state import State
from conflict_interface.data_types.state import universal_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode


class VisibilityMode(Enum, metaclass=DefaultEnumMeta):
    ALL = 1
    ONLY_VISIBLE = 2
    ALL_REDUCED_INFORMATION = 3


@dataclass
class PlayerState(State):
    C = "ultshared.UltPlayerState"
    STATE_TYPE = 1
    players: HashMap[int, PlayerProfile]
    teams: HashMap[int, TeamProfile]

    MAPPING = {
        "players": "players",
        "teams": "teams"
    }

    def update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        universal_update(self, other, path, rp)