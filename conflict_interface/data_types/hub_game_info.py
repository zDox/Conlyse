from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from conflict_interface.data_types.custom_types import DefaultEnumMeta
from conflict_interface.data_types.game_object import GameObject


class HubGameState(Enum, metaclass=DefaultEnumMeta):
    UNDEFINED = "undefined"
    NONE = "none"
    READY_TO_JOIN = "readytojoin"
    RUNNING = "running"
    FINISHED = "finished"


def openslots_to_currentplayers(obj, openslots):
    return int(obj["nrofplayers"]) - int(openslots)


def timescale_to_speedfactor(time_scale):
    return int(1/float(time_scale))


@dataclass
class HubGameInfo:
    """
    Its a dataclass for the getInternationalGames webapi
    entry point to model that retrieved data
    """
    game_id: int
    mod_id: int
    mod_version: int
    scenario_id: int
    scenario_version_id: int
    season_id: int
    start_of_game: datetime
    open_slots: int
    max_players: int
    day_of_game: int
    end_of_game: bool
    last_login: datetime
    creator_id: int
    title: str
    comment: str
    anti_cheat_level: int
    ranked: bool
    demo_game: bool
    min_rank: int
    managed_game: bool
    creation_date: datetime
    ai_level: int
    victory_points: int
    victory_condition: int
    team_victory_points: int
    country_selection: bool
    number_of_teams: int
    beta_game: bool
    min_activity: int
    peace_period: int
    peace_period_ai: int
    honor_period: int
    tournament_id: int
    tournament_round_id: int
    start_level: int
    gold_mark_limit_level: int
    anonymous_round: bool
    deleted: bool
    gold_round: bool
    game_status: int
    last_statistics_update: datetime
    unit_pack: int
    xp_boost_factor: int
    time_scale: float
    update_timestamp: datetime
    max_rank: int
    max_join_day: int
    map_reference: str
    state: HubGameState

    MAPPING = {
            'game_id': 'gameID',
            'mod_id': 'modID',
            'mod_version': 'modVersionID',
            'scenario_id': 'scenarioID',
            'scenario_version_id': 'scenarioVersionID',
            'season_id': 'seasonID',
            'start_of_game': 'startofgame2',
            'open_slots': 'openSlots',
            'max_players': 'nrofplayers',
            'day_of_game': 'dayofgame',
            'end_of_game': 'endofgame2',
            'last_login': 'lastlogintime',
            'creator_id': 'creatorID',
            'title': 'title',
            'comment': 'comment',
            'anti_cheat_level': 'antiCheatLevel',
            'ranked': 'ranked',
            'demo_game': 'demoGame',
            'min_rank': 'minRank',
            'managed_game': 'managedGame',
            'creation_date': 'crdate',
            'ai_level': 'aiLevel',
            'victory_points': 'victoryPoints',
            'victory_condition': 'victoryCondition',
            'team_victory_points': 'teamVictoryPoints',
            'country_selection': 'countrySelection',
            'number_of_teams': 'numberOfTeams',
            'beta_game': 'betaGame',
            'min_activity': 'minActivity',
            'peace_period': 'peacePeriod',
            'peace_period_ai': 'peacePeriodAI',
            'honor_period': 'honorPeriod',
            'tournament_id': 'tournamentID',
            'tournament_round_id': 'tournamentRoundID',
            'start_level': 'startLevel',
            'gold_mark_limit_level': 'goldmarkLimitLevel',
            'anonymous_round': 'anonymousRound',
            'deleted': 'deleted',
            'gold_round': 'goldRound',
            'game_status': 'gameStatus',
            'last_statistics_update': 'lastStatisticsUpdate',
            'unit_pack': 'unitPack',
            'xp_boost_factor': 'xpBoostFactor',
            'time_scale': 'timeScale',
            'update_timestamp': 'updateTstamp',
            'max_rank': 'maxRank',
            'max_join_day': 'maxJoinDay',
            'map_reference': 'mapReference',
            'state': 'state',
        }
