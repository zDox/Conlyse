from data_types import GameInfo, PlayerProfile, TeamProfile


def parse_international_games(data):
    res = []
    for item in data:
        res.append(GameInfo.from_dict(item["properties"]))
    return res


"""
Parse GameStateUpdate
"""


def parse_player_state(obj):
    players = {}
    for player in list(obj["players"].values())[1:]:
        players[player["playerID"]] = PlayerProfile.from_dict(player)

    teams = {}
    for team in list(obj["teams"].values())[1:]:
        teams[team["teamID"]] = TeamProfile.from_dict(team)
    return players, teams
