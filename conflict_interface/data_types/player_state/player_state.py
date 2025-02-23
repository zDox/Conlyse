from conflict_interface.utils import GameObject, HashMap

from dataclasses import dataclass
from enum import Enum

from conflict_interface.utils import DefaultEnumMeta
from conflict_interface.data_types.player_state.player_profile import PlayerProfile
from conflict_interface.data_types.player_state.team_profile import TeamProfile

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
class PlayerState(GameObject):
    STATE_ID = 1
    players: HashMap[int, PlayerProfile]
    teams: HashMap[int, TeamProfile]

    MAPPING = {
        "players": "players",
        "teams": "teams"
    }


    def get_players(self, terra_incognita_feature: bool,
                    visibility_mode=VisibilityMode.ALL):

        if not terra_incognita_feature:
            return self.players
        match terra_incognita_feature:
            case VisibilityMode.ONLY_VISIBLE:
                return self.get_visible_players()
            case VisibilityMode.ALL_REDUCED_INFORMATION:
                return self.get_reduced_players()
            case _:
                return self.players

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
