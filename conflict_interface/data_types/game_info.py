from conflict_interface.utils import GameObject

from dataclasses import dataclass
from datetime import datetime

from conflict_interface.utils import MappedValue, \
        unixtimestamp_to_datetime


def openslots_to_currentplayers(obj, openslots):
    return int(obj["numberOfPlayers"]) - int(openslots)


def timescale_to_speedfactor(time_scale):
    return int(1/float(time_scale))


def parse_game_features(game_features):
    if game_features is None:
        return
    return [GameFeature.from_dict(game_feature)
            for game_feature in list(game_features["idFeatures"].values())[1:]]


@dataclass
class GameFeature(GameObject):
    feature_id: int
    value: int
    value_name: str
    enabled: bool
    published: bool
    name: str
    description: str

    MAPPING = {
        "feature_id": "featureID",
        "value": "value",
        "value_name": "valueName",
        "enabled": "enabled",
        "published": "published",
        "name": "name",
        "description": "description",
    }


@dataclass
class GameInfo(GameObject):
    map_id: int
    scenario_id: int
    start_of_game: datetime
    current_players: int
    max_players: int
    day_of_game: int
    next_day_time: datetime
    next_heal_time: datetime
    end_of_game: datetime
    game_ended: bool
    ranked: bool
    demo_game: bool
    country_selection: bool
    number_of_teams: int
    gold_round: bool
    speed_factor: int
    game_features: list[GameFeature]

    MAPPING = {
            'map_id': 'mapID',
            'scenario_id': 'scenarioID',
            'start_of_game': MappedValue('startOfGame',
                                         unixtimestamp_to_datetime),
            'current_players': MappedValue('openSlots',
                                           openslots_to_currentplayers,
                                           needs_entire_obj=True),
            'max_players': 'numberOfPlayers',
            'day_of_game': 'dayOfGame',

            'end_of_game': MappedValue('endOfGame',
                                       unixtimestamp_to_datetime),
            'game_ended': 'gameEnded',
            'next_day_time': MappedValue('nextDayTime',
                                         unixtimestamp_to_datetime),
            'next_heal_time': MappedValue('nextHealTime',
                                          unixtimestamp_to_datetime),
            'ranked': 'ranked',
            'demo_game': 'demoGame',
            'country_selection': 'countrySelection',
            'number_of_teams': 'numberOfTeams',
            'gold_round': 'goldRound',
            'speed_factor': MappedValue('timeScale', timescale_to_speedfactor),
            "game_features": MappedValue("gameFeatures", parse_game_features),
        }
