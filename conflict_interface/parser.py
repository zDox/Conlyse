from data_types.team_profile import TeamProfile
from data_types.player_profile import PlayerProfile
from data_types.hub_game_info import HubGameInfo


def parse_international_games(data):
    res = []
    for item in data:
        res.append(HubGameInfo.from_dict(item["properties"]))
    return res


"""
Parse GameStateUpdate
"""


