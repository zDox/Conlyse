
from dataclasses import dataclass
from typing import Optional
from typing import get_type_hints

from conflict_interface.data_types.newest.version import VERSION
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.data_types.newest.custom_types import DateTimeSecondsInt

from conflict_interface.api.hub_types.hub_game_state_enum import HubGameState



@conflict_serializable(SerializationCategory.DATACLASS, version = -1)
@dataclass
class GameLogin:
    achievement_title_id: int
    alliance_id: int
    faction: int
    login: str
    player_level: int
    site_user_id: int
    team_id: int

    MAPPING = {
        'achievement_title_id': 'achievementTitleItemID',
        'alliance_id': 'allianceID',
        'faction': 'faction',
        'login': 'login',
        'player_level': 'playerLevel',
        'site_user_id': 'siteUserID',
        'team_id': 'teamID',
    }

    _type_hints = None

    @classmethod
    def get_type_hints_cached(cls):
        if cls._type_hints is None:
            cls._type_hints = get_type_hints(cls)
        return cls._type_hints

@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class HubGameProperties:
    game_id: int
    mod_id: int
    mod_version: int
    scenario_id: int
    scenario_version_id: int
    season_id: int
    start_of_game: DateTimeSecondsInt
    open_slots: int
    max_players: int
    day_of_game: int
    end_of_game: bool
    last_login: DateTimeSecondsInt
    creator_id: int
    title: str
    comment: str
    anti_cheat_level: int
    ranked: bool
    demo_game: bool
    min_rank: int
    managed_game: bool
    creation_date: DateTimeSecondsInt
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
    last_statistics_update: DateTimeSecondsInt
    unit_pack: int
    xp_boost_factor: int
    time_scale: float
    update_timestamp: str
    max_rank: int
    max_join_day: int
    map_reference: str
    state: HubGameState

    end_day_of_game: int
    alliance_game: int
    nations_cup_tournament_region: Optional[str] # TODO check if string is correct type
    engine: str
    is_system_game: bool
    auto_update_interval: int
    open_challenge: int
    db_type: Optional[str]
    db: str
    mod_document_id: Optional[str]
    alliance_a: int
    alliance_b: int
    pause_start_time: int
    last_access_time: Optional[str]
    start_date: int
    ticket: int
    anticheat_set: str
    pause_modus: int
    password_set: str
    gs: str
    language: str
    quest_province_conquer: int
    team_settings: str
    min_rank_image: Optional[str]
    min_rank_label: Optional[str]



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
        "min_rank_image": "minrankimage",
        "min_rank_label": "minranklabel",
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
        "end_day_of_game": "endDayOfGame",
        "alliance_game": "allianceGame",
        "nations_cup_tournament_region": "nationsCupTournamentRegion",
        "engine": "engine",
        "is_system_game": "isSystemGame",
        "auto_update_interval": "autoUpdateInterval",
        "open_challenge": "openChallenge",
        "db_type": "dbType",
        "mod_document_id": "modDocumentID",
        "alliance_a": "allianceA",
        "alliance_b": "allianceB",
        "db": "db",
        "pause_start_time": "pauseStartTime",
        "last_access_time": "lastaccesstime",
        "start_date": "startDate",
        "ticket": "ticket",
        "anticheat_set": "anticheatset",
        "pause_modus": "pauseModus",
        "password_set": "passwordset",
        "gs": "gs",
        "language": "language",
        "quest_province_conquer": "questProvinceConquer",
        "team_settings": "teamSettings"
    }

    _type_hints = None

    @classmethod
    def get_type_hints_cached(cls):
        if cls._type_hints is None:
            cls._type_hints = get_type_hints(cls)
        return cls._type_hints

@conflict_serializable(SerializationCategory.DATACLASS, version = -1)
@dataclass
class HubGame:
    C = "hup.model.games.Game"
    """
    Its a dataclass for the getInternationalGames webapi
    entry point to model that retrieved data
    """
    properties: HubGameProperties
    logins: list[GameLogin] = None
    MAPPING = {
        "properties": "properties",
        "logins": "logins",
    }
    _type_hints = None

    @classmethod
    def get_type_hints_cached(cls):
        if cls._type_hints is None:
            cls._type_hints = get_type_hints(cls)
        return cls._type_hints

