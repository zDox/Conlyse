from dataclasses import dataclass
from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable
from conflict_interface.data_types.player_state.player_profile import PlayerProfile
from conflict_interface.data_types.player_state.team_profile import TeamProfile
from conflict_interface.data_types.state import State
from conflict_interface.data_types.state import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode

@binary_serializable(SerializationCategory.ENUM)
class VisibilityMode(Enum, metaclass=DefaultEnumMeta):
    ALL = 1
    ONLY_VISIBLE = 2
    ALL_REDUCED_INFORMATION = 3

@binary_serializable(SerializationCategory.DATACLASS)
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
                    rp.add(path + ["players", player.player_id], None, player)
                self.players[player.player_id] = player
            else:
                self.players[player.player_id].update(
                    player,
                    path + ["players", player.player_id],
                    rp
                )