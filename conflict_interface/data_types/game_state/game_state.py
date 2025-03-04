from typing import cast
from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.admin_state.admin_state import AdminState
from conflict_interface.data_types.ai_state.ai_state import AIState
from conflict_interface.data_types.army_state.army_state import ArmyState
from conflict_interface.data_types.build_queue_state import BuildQueueState
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.exploration_state import ExplorationState
from conflict_interface.data_types.game_event_state import GameEventState
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.in_game_alliance_state import InGameAllianceState
from conflict_interface.data_types.location_state import LocationState
from conflict_interface.data_types.map_info_state import MapInfoState
from conflict_interface.data_types.mission_state import MissionState
from conflict_interface.data_types.player_state import PlayerState
from conflict_interface.data_types.newspaper_state import NewspaperState
from conflict_interface.data_types.map_state import MapState
from conflict_interface.data_types.premium_state import PremiumState
from conflict_interface.data_types.quest_state import QuestState
from conflict_interface.data_types.resource_state import ResourceState
from conflict_interface.data_types.foreign_affairs_state import ForeignAffairsState
from conflict_interface.data_types.spy_state import SpyState
from conflict_interface.data_types.mod_state import ModState
from conflict_interface.data_types.game_info_state import GameInfoState
from conflict_interface.data_types.research_state import ResearchState
from conflict_interface.data_types.configuration_state import ConfigurationState
from conflict_interface.data_types.state import State
from conflict_interface.data_types.statistic_state import StatisticState
from conflict_interface.data_types.triggered_tutorial_state.triggered_tutorial_state import TriggeredTutorialState
from conflict_interface.data_types.tutorial_state import TutorialState
from conflict_interface.data_types.user_inventory_state import UserInventoryState
from conflict_interface.data_types.user_options_state import UserOptionsState
from conflict_interface.data_types.user_sms_state import UserSMSState
from conflict_interface.data_types.wheel_of_fortune_state import WheelOfFortuneState

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
class States(GameObject):
    C = "java.util.HashMap"
    player_state: Optional[PlayerState]
    newspaper_state: Optional[NewspaperState]
    map_state: Optional[MapState]
    resource_state: Optional[ResourceState]
    foreign_affairs_state: Optional[ForeignAffairsState]
    army_state: Optional[ArmyState]
    spy_state: Optional[SpyState]
    map_info_state: Optional[MapInfoState]
    admin_state: Optional[AdminState]
    statistic_state: Optional[StatisticState]
    mod_state: Optional[ModState]
    game_info_state: Optional[GameInfoState]
    ai_state: Optional[AIState]
    premium_state: Optional[PremiumState]
    user_options_state: Optional[UserOptionsState]
    user_inventory_state: Optional[UserInventoryState]
    user_sms_state: Optional[UserSMSState]
    tutorial_state: Optional[TutorialState]
    build_queue_state: Optional[BuildQueueState]
    location_state: Optional[LocationState]
    triggered_tutorial_state: Optional[TriggeredTutorialState]
    wheel_of_fortune_state: Optional[WheelOfFortuneState]
    research_state: Optional[ResearchState]
    game_event_state: Optional[GameEventState]
    in_game_alliance_state: Optional[InGameAllianceState]
    exploration_state: Optional[ExplorationState]
    quest_state: Optional[QuestState]
    configuration_state: Optional[ConfigurationState]
    mission_state: Optional[MissionState]

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


    def update(self, new_fields: "States"):
        """
        Call the update method of each state that has a update and hand of the state as dict

        :param new_fields: The new fields to update with (dict)
        :return: None
        """
        if new_fields is None:
            return
        for field in self.__annotations__.keys():
            state = getattr(self, field)
            if state is None:
                continue
            if not issubclass(type(state), State):
                continue
            state = cast(State, state)
            state.time_stamp = getattr(state, "time_stamp")
            state.state_id = getattr(state, "state_id")

            if not callable(getattr(state, "update", None)):
                continue
            getattr(self, field).update(state)


@dataclass
class GameState(State):
    C = "ultshared.UltGameState"
    state_type: int
    state_id: str
    time_stamp: str
    states: States
    action_results: Optional[HashMap[str, int]]

    MAPPING = {
        "states": "states",
        "action_results": "actionResults"
    }

    def get_state_ids_and_time_stamps(self):
        state_ids = HashMap()
        time_stamps = HashMap()
        for state in self.states.__annotations__.keys():
            state = getattr(self.states, state)
            if state is None:
                continue
            state_ids[state.state_type] = state.state_id
            time_stamps[state.state_type] = state.time_stamp
        if len(time_stamps) == 0 or len(state_ids) == 0:
            return None, None
        return state_ids, time_stamps

    def update(self, new_state: "GameState"):
        self.action_results = new_state.action_results
        self.states.update(new_state.states)
