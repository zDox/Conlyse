from dataclasses import dataclass

import PlayerProfile
import TeamProfile


@dataclass
class PlayerState:
    STATE_ID = 1
    players: dict[int, PlayerProfile]
    teams: dict[int, TeamProfile]

    def update(self, new_state):
        self.players = new_state.players
        self.teams = new_state.teams

    @classmethod
    def from_dict(cls, obj):
        players = {int(player_id): PlayerProfile.from_dict(player)
                   for player_id, player in list(obj["players"].items())[1:]}

        teams = {int(team_id): TeamProfile.from_dict(team)
                 for team_id, team in list(obj["teams"].items())[1:]}

        return cls(**{
            "players": players,
            "teams": teams,
        })
