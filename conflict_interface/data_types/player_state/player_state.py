from typing import override

from conflict_interface.data_types.custom_types import DefaultEnumMeta, HashMap
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass
from enum import Enum


from conflict_interface.data_types.player_state.player_profile import PlayerProfile
from conflict_interface.data_types.player_state.team_profile import TeamProfile
from conflict_interface.data_types.state import State

"""
Not implemented
resetExplorationCaches
getVisiblePlayers
getReducedPlayers
getMaxTeamSize
"""


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

    # TODO: Implement this method
    def get_players(self, terra_incognita_feature: bool,
                    visibility_mode=VisibilityMode.ALL):
        raise NotImplementedError()

    def reset_exploration_caches(self):
        raise NotImplementedError()

    def get_player_ids(self):
        return list(self.players.keys())

    def get_player(self, player_id):
        return self.players.get(player_id)

    def get_teams(self):
        return {team.get_team_id(): team for team in self.teams.values()
                if not team.is_disbanded()}

    def get_team_members(self, team_id):
        return [player for player in self.players.values()
                if player.get_team_id() == team_id]

    def get_human_team_members(self, team_id):
        return [player for player in self.players.values()
                if player.get_team_id() == team_id
                and not player.is_computer_player()]

    def get_current_team_limit(a, b):
        return a // b + 1

    def get_team(self, team_id):
        return self.teams.get(team_id)

    def are_players_in_a_team(self, player_id_1: int, player_id_2: int):
        player_1 = self.get_player(player_id_1)
        player_2 = self.get_player(player_id_2)
        return (player_id_1 == player_id_2 or
                (player_1.get_team_id() > 0 and
                 player_1.get_team_id() == player_2.get_team_id()))

    def get_filtered_players(self, include_ai, include_human,
                             excluded_player_id):
        filtered_players = []
        for value in self.players.values():
            if value.playerID != excluded_player_id and value.playerID > -1:
                if ((value.is_ai_player() and include_ai and not
                     value.is_defeated()) or (not value.is_ai_player()
                                              and include_human)):
                    filtered_players.append(value)
        return filtered_players

    @override
    def update(self, other: GameObject):
        if not isinstance(other, PlayerState):
            raise TypeError("UPDATE ERROR: Cannot update PlayerState with object of type: "
                            f"{type(other)}")

        if not other.players is None:
            # iterate through playerprofiles and update them
            for player_id, player in other.players.items():
                if player_id in self.players:
                    if self.players[player_id] is None:
                        self.players[player_id] = player
                    self.players[player_id].update(player)
                else:
                    self.players[player_id] = player

        if not other.teams is None:
            # iterate through teamprofiles and update them
            for team_id, team in other.teams.items():
                if team_id in self.teams:
                    if self.teams[team_id] is None:
                        self.teams[team_id] = team
                    self.teams[team_id].update(team)
                else:
                    self.teams[team_id] = team