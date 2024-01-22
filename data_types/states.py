
from data_types.team_profile import TeamProfile
from data_types.player_profile import PlayerProfile
from data_types.province import Province
from data_types.utils import UpdatableClass
from data_types.static_map_data import StaticMapData
from data_types.game_info import GameInfo

"""
from data_types.article import Article
from data_types.relationship import Relationship
from data_types.army import Army
from data_types.upgrade import Upgrade
from data_types.unit_type import UnitType
from data_types.research_type import ResearchType
"""
from pprint import pprint
from dataclasses import dataclass


"""
The following are all states but not every state
is implemented

STATE_TYPE_GAME_STATE: 0,
STATE_TYPE_PLAYER_STATE: 1,
STATE_TYPE_NEWSPAPER_STATE: 2,
STATE_TYPE_MAP_STATE: 3,
STATE_TYPE_RESOURCE_STATE: 4,
STATE_TYPE_FOREIGN_AFFAIRS_STATE: 5,
STATE_TYPE_ARMY_STATE: 6,
STATE_TYPE_SPY_STATE: 7,
STATE_TYPE_MAP_INFO_STATE: 8,
STATE_TYPE_ADMIN_STATE: 9,
STATE_TYPE_STATISTIC_STATE: 10,
STATE_TYPE_MOD_STATE: 11,
STATE_TYPE_GAME_INFO_STATE: 12,
STATE_TYPE_AI_STATE: 13,
STATE_TYPE_PREMIUM_STATE: 14,
STATE_TYPE_USER_OPTIONS_STATE: 15,
STATE_TYPE_USER_INVENTORY_STATE: 16,
STATE_TYPE_USER_SMS_OPTION_STATE: 17,
STATE_TYPE_TUTORIAL_STATE: 18,
STATE_TYPE_BUILD_QUEUE_STATE: 19,
STATE_TYPE_LOCATION_STATE: 20,
STATE_TYPE_TRIGGERED_TUTORIAL: 21,
STATE_TYPE_WHEEL_OF_FORTUNE_STATE: 22,
STATE_TYPE_RESEARCH_STATE: 23,
STATE_TYPE_GAME_EVENT_STATE: 24,
STATE_TYPE_IN_GAME_ALLIANCE: 25,
STATE_TYPE_EXPLORATION_STATE: 26,
STATE_TYPE_QUEST_STATE: 27,
STATE_TYPE_CONFIGURATION_STATE: 28
STATE_TYPE_MISSION_STATE: 29
"""


@dataclass
class PlayerState:
    STATE_ID = 1
    players: dict[int, PlayerProfile]
    teams: dict[int, TeamProfile]

    @classmethod
    def from_dict(cls, obj):
        players = {}
        for player in list(obj["players"].values())[1:]:
            players[player["playerID"]] = PlayerProfile.from_dict(player)

        teams = {}
        for team in list(obj["teams"].values())[1:]:
            teams[team["teamID"]] = TeamProfile.from_dict(team)

        return cls(**{
            "players": players,
            "teams": teams,
            })

    def update(self, new_state):
        self.players = new_state.players
        self.teams = new_state.teams


@dataclass
class NewspaperState:
    STATE_ID = 2
    # articles: list(Article)


@dataclass
class MapState:
    STATE_ID = 3
    provinces: dict[int, Province]
    # Provinces which are owned by the current player
    # province_properties: list(ProvinceProperty)

    @classmethod
    def from_dict(cls, obj):
        provinces = {}
        for province in obj["map"]["locations"][1]:
            # pprint(province)
            province = Province.from_dict(province)
            provinces[province.id] = province

        return cls(**{
            "provinces": provinces
        })

    def update(self, new_state):
        for province in new_state.provinces:
            self.provinces[province.id].update(province)

    def set_static_map_data(self, static_map_data: StaticMapData):
        for province in static_map_data.provinces:
            self.provinces[province.id].set_static_province(province)


@dataclass
class ResourceState:
    STATE_ID = 4
    # Trading, Own Resources


@dataclass
class ForeignAffairsState:
    STATE_ID = 5
    # relations: list(Relationship)


@dataclass
class ArmyState:
    STATE_ID = 6
    # armies: list(Army)


@dataclass
class SpyState:
    STATE_ID = 7
    # Spies, Nations, SpyReports


@dataclass
class MapInfoState:
    STATE_ID = 8


@dataclass
class AdminState:
    STATE_ID = 8


@dataclass
class StatisticState:
    STATE_ID = 9


@dataclass
class ModState:
    STATE_ID = 11
    # upgrades: list(Upgrade)
    # unit_types: list(UnitType)
    # research_types: list(ResearchType)


@dataclass
class GameInfoState:
    STATE_ID = 12
    game_info: GameInfo

    @classmethod
    def from_dict(cls, obj):
        return cls(**{
            "game_info": GameInfo.from_dict(obj)
            })


@dataclass
class AIState:
    STATE_ID = 13


@dataclass
class PremiumState:
    STATE_ID = 14


@dataclass
class UserOptionsState:
    STATE_ID = 15


@dataclass
class UserInventoryState:
    STATE_ID = 16


@dataclass
class UserSMSState:
    STATE_ID = 17


@dataclass
class TutorialState:
    STATE_ID = 18


@dataclass
class BuildQueueState:
    STATE_ID = 19


@dataclass
class LocationState:
    STATE_ID = 20


@dataclass
class TriggeredTutorialState:
    STATE_ID = 21


@dataclass
class WheelOfFortuneState:
    STATE_ID = 22


@dataclass
class ResearchState:
    STATE_ID = 23
    # current_researches: list(Research)
    # completed_researches: list(Research)
    research_slots: int


@dataclass
class GameEventState:
    STATE_ID = 24


@dataclass
class InGameAllianceState:
    STATE_ID = 25


@dataclass
class ExplorationState:
    STATE_ID = 26


@dataclass
class QuestState:
    STATE_ID = 27


@dataclass
class ConfigurationState:
    STATE_ID = 28


@dataclass
class MissionState:
    STATE_ID = 29


@dataclass
class States(UpdatableClass):
    player_state: PlayerState
    newspaper_state: NewspaperState
    map_state: MapState
    resource_state: ResourceState
    foreign_affairs_state: ForeignAffairsState
    army_state: ArmyState
    spy_state: SpyState
    map_info_state: MapInfoState
    admin_state: AdminState
    statistic_state: StatisticState
    mod_state: ModState
    game_info_state: GameInfoState
    ai_state: AIState
    premium_state: PremiumState
    user_options_state: UserOptionsState
    user_inventory_state: UserInventoryState
    user_sms_state: UserSMSState
    tutorial_state: TutorialState
    build_queue_state: BuildQueueState
    location_state: LocationState
    triggered_tutorial_state: TriggeredTutorialState
    wheel_of_fortune_state: WheelOfFortuneState
    research_state: ResearchState
    game_event_state: GameEventState
    in_game_alliance_state: InGameAllianceState
    exploration_state: ExplorationState
    quest_state: QuestState
    configuration_state: ConfigurationState
    mission_state: MissionState

    @classmethod
    def from_dict(cls, obj):
        parsed_data = {}
        for i, (field_name, field_type) \
                in enumerate(cls.__annotations__.items()):
            parsed_data[field_name] = None

            # if state is in object and state is implemented
            if str(i+1) in obj \
                    and callable(getattr(field_type, "from_dict", None)):
                parsed_data[field_name] = field_type.from_dict(
                        obj[str(i+1)])

        return cls(**parsed_data)

    def update(self, new_class):
        for field in self.__annotations__.keys():
            if not callable(getattr(field, "update", None)):
                continue

            getattr(self, field).update(new_class[field])
