from dataclasses import dataclass
from enum import Enum

from ..custom_types import DefaultEnumMeta
from ..custom_types import HashMap
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..player_state.player_profile import PlayerProfile
from ..player_state.team_profile import TeamProfile
from ..state import State
from ..update_helpers import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode


from ..version import VERSION
@conflict_serializable(SerializationCategory.ENUM, version = VERSION)
class VisibilityMode(Enum, metaclass=DefaultEnumMeta):
    ALL = 1
    ONLY_VISIBLE = 2
    ALL_REDUCED_INFORMATION = 3

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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

    def update(self, other: "PlayerState", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        state_update(self, other, path, rp)

        for player in other.players.values():
            if player.player_id not in self.players:
                if rp:
                    rp.add(path + ["players", player.player_id], player)
                self.players[player.player_id] = player
            else:
                self.players[player.player_id].update(
                    player,
                    path + ["players", player.player_id],
                    rp
                )