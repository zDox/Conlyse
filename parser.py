from data_types.team_profile import TeamProfile
from data_types.player_profile import PlayerProfile
from data_types.game_info import GameInfo


def parse_international_games(data):
    res = []
    for item in data:
        res.append(GameInfo.from_dict(item["properties"]))
    return res


"""
Parse GameStateUpdate
"""


