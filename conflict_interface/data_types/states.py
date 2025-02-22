from dataclasses import dataclass
from typing import Optional

from .player_state import PlayerState
from .newspaper_state import NewspaperState
from .map_state import MapState
from .resource_state import ResourceState
from .foreign_affairs_state import ForeignAffairsState
from .army_state import ArmyState
from .spy_state import SpyState
from .mod_state import ModState
from .game_info_state import GameInfoState
from .research_state import ResearchState
from .configuration_state import ConfigurationState
from ..utils import GameObject

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
class MapInfoState(GameObject):
    STATE_ID = 8


@dataclass
class AdminState(GameObject):
    STATE_ID = 9


@dataclass
class StatisticState(GameObject):
    STATE_ID = 10


@dataclass
class AIState(GameObject):
    STATE_ID = 13


@dataclass
class PremiumState(GameObject):
    STATE_ID = 14


@dataclass
class UserOptionsState(GameObject):
    STATE_ID = 15


@dataclass
class UserInventoryState(GameObject):
    STATE_ID = 16


@dataclass
class UserSMSState(GameObject):
    STATE_ID = 17


@dataclass
class TutorialState(GameObject):
    STATE_ID = 18


@dataclass
class BuildQueueState(GameObject):
    STATE_ID = 19


@dataclass
class LocationState(GameObject):
    STATE_ID = 20


@dataclass
class TriggeredTutorialState(GameObject):
    STATE_ID = 21


@dataclass
class WheelOfFortuneState(GameObject):
    STATE_ID = 22


@dataclass
class GameEventState(GameObject):
    STATE_ID = 24


@dataclass
class InGameAllianceState(GameObject):
    STATE_ID = 25


@dataclass
class ExplorationState(GameObject):
    STATE_ID = 26


@dataclass
class QuestState(GameObject):
    STATE_ID = 27


@dataclass
class MissionState(GameObject):
    STATE_ID = 29


@dataclass
class States(GameObject):
    player_state: PlayerState
    newspaper_state: NewspaperState
    map_state: MapState
    resource_state: ResourceState
    foreign_affairs_state: ForeignAffairsState
    army_state: ArmyState
    spy_state: SpyState
    map_info_state: Optional[MapInfoState]
    admin_state: Optional[AdminState]
    statistic_state: Optional[StatisticState]
    mod_state: ModState
    game_info_state: GameInfoState
    ai_state: Optional[AIState]
    premium_state: Optional[PremiumState]
    user_options_state: Optional[UserOptionsState]
    user_inventory_state: Optional[UserInventoryState]
    user_sms_state: Optional[UserSMSState]
    tutorial_state: Optional[TutorialState]
    build_queue_state: BuildQueueState
    location_state: Optional[LocationState]
    triggered_tutorial_state: Optional[TriggeredTutorialState]
    wheel_of_fortune_state: Optional[WheelOfFortuneState]
    research_state: ResearchState
    game_event_state: GameEventState
    in_game_alliance_state: Optional[InGameAllianceState]
    exploration_state: Optional[ExplorationState]
    quest_state: Optional[QuestState]
    configuration_state: ConfigurationState
    mission_state: MissionState

    MAPPING = {
        "player_state": "1",
        "newspaper_state": "2",
        "map_state": "3",
        "resource_state": "4",
        "foreign_affairs_state": "5",
        "army_state": "6",
        "spy_state": "7",
        "map_info_state": "8",
        "admin_state": "9",
        "statistic_state": "10",
        "mod_state": "11",
        "game_info_state": "12",
        "ai_state": "13",
        "premium_state": "14",
        "user_options_state": "15",
        "user_inventory_state": "16",
        "user_sms_state": "17",
        "tutorial_state": "18",
        "build_queue_state": "19",
        "location_state": "20",
        "triggered_tutorial_state": "21",
        "wheel_of_fortune_state": "22",
        "research_state": "23",
        "game_event_state": "24",
        "in_game_alliance_state": "25",
        "exploration_state": "26",
        "quest_state": "27",
        "configuration_state": "28",
        "mission_state": "29",
    }


    def update(self, new_class):
        for field in self.__annotations__.keys():
            if not callable(getattr(field, "update", None)):
                continue

            getattr(self, field).update(new_class[field])
