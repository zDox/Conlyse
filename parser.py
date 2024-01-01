from data_types import GameInfo


def parse_international_games(data):
    res = []
    for item in data:
        print(item)
        res.append(GameInfo.from_dict(item["properties"]))
    return res
