from .data_types import HubGameInfo


def parse_international_games(data):
    res = []
    for item in data:
        res.append(HubGameInfo.from_dict(item["properties"]))
    return res
