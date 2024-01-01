from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class GameInfoState(Enum):
    READY_TO_JOIN = 0


@dataclass
class GameInfo():
    game_id: int
    mod_id: int
    mod_version: int
    scenario_id: int
    scenario_version_id: int
    season_id: int
    start_of_game: date
    current_players: int
    max_players: int
    day_of_game: int
    end_of_game: bool
    last_login: date
    creator_id: int
    title: str
    comment: str
    anti_cheat_level: int
    ranked: bool
    demo_game: bool
    min_rank: int
    managed_game: bool
    creation_date: date
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
    last_statistics_update: date
    unit_pack: int
    xp_boost_factor: int
    speed_factor: int
    update_timestamp: date
    max_rank: int
    max_join_day: int
    map_reference: str
    state: GameInfoState

    @classmethod
    def from_dict(cls, obj):
        json_field_mapping = {
            'game_id': 'gameID',
            'mod_id': 'modID',
            'mod_version': 'modVersionID',
            'scenario_id': 'scenarioID',
            'scenario_version_id': 'scenarioVersionID',
            'season_id': 'seasonID',
            'start_of_game': 'startofgame2',
            'current_players': 'openSlots',
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
            'speed_factor': 'timeScale',
            'update_timestamp': 'updateTstamp',
            'max_rank': 'maxRank',
            'max_join_day': 'maxJoinDay',
            'map_reference': 'mapReference',
            'state': 'state',
        }
        field_names = [f.name for f in cls.__dataclass_fields__.values()]
        parsed_data = {}
        for f_name in field_names:
            val = obj[json_field_mapping[f_name]]
            if not val:
                parsed_data[f_name] = None
                continue
            if val.isdigit():
                parsed_data[f_name] = int(val)
            else:
                parsed_data[f_name] = val

        """
        parsed_data = {
            k: int(obj[json_field_mapping[k]])
            if  else
            obj[json_field_mapping[k]]
            for k in field_names
        }
        """
        # Custom conversions for specific fields
        parsed_data['start_of_game'] = datetime.utcfromtimestamp(
                int(obj.get('startofgame2', 0)))
        parsed_data['last_login'] = datetime.utcfromtimestamp(
                int(obj.get('lastlogintime', 0))
                ) if obj.get('lastlogintime') else None
        parsed_data['creation_date'] = datetime.utcfromtimestamp(
                int(obj.get('crdate', 0)))
        parsed_data['last_statistics_update'] = datetime.utcfromtimestamp(
                int(obj.get('lastStatisticsUpdate', 0)))
        print(obj.get('updateTstamp'))
        parsed_data['update_timestamp'] = datetime.strptime(
                obj.get('updateTstamp'), "%Y-%m-%d %H:%M:%S")

        parsed_data['state'] = GameInfoState.READY_TO_JOIN \
            if obj.get("state") == "ready" else None
        return cls(**parsed_data)
