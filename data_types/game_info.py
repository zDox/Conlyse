from data_types.utils import JsonMappedClass, MappedValue

from dataclasses import dataclass
from datetime import date, datetime


def unixtimestamp_to_datetime(timestamp):
    return datetime.utcfromtimestamp(int(timestamp)) \
            if timestamp else None


def unixtimestamp_milli_to_datetime(timestamp):
    return datetime.utcfromtimestamp(int(timestamp)/1000) \
            if timestamp else None


def openslots_to_currentplayers(obj, openslots):
    return int(obj["numberOfPlayers"]) - int(openslots)


def timescale_to_speedfactor(time_scale):
    return int(1/float(time_scale))


@dataclass
class GameInfo(JsonMappedClass):
    map_id: int
    scenario_id: int
    start_of_game: date
    current_players: int
    max_players: int
    day_of_game: int
    next_day_time: date
    next_heal_time: date
    end_of_game: date
    game_ended: bool
    ranked: bool
    demo_game: bool
    country_selection: bool
    number_of_teams: int
    gold_round: bool
    speed_factor: int

    mapping = {
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
                                         unixtimestamp_milli_to_datetime),
            'next_heal_time': MappedValue('nextHealTime',
                                          unixtimestamp_milli_to_datetime),
            'ranked': 'ranked',
            'demo_game': 'demoGame',
            'country_selection': 'countrySelection',
            'number_of_teams': 'numberOfTeams',
            'gold_round': 'goldRound',
            'speed_factor': MappedValue('timeScale', timescale_to_speedfactor),
        }
