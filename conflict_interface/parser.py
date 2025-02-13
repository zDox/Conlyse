from .data_types import HubGameInfo


def parse_international_games(data):
    res = {}
    for item in data:
        game = HubGameInfo.from_dict(item["properties"])
        res[game.game_id] = game
    return res
