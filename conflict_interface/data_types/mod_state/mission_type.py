from dataclasses import dataclass

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.mod_state.configuration import MissionTypeFrontEndConfig
from conflict_interface.data_types.mod_state.mission_reward import MissionReward


@dataclass
class MissionType:
    C = "ultshared.modding.types.UltMissionType"
    item_id: int
    help_title: str
    help_description: str
    long_description: str
    short_description: str
    title: str
    start_triggers: ArrayList[int] #TODO check typing
    end_triggers: ArrayList[int] #TODO check typing
    fail_triggers: ArrayList[int] #TODO check typing

    rewards: ArrayList[MissionReward]
    frontend_config: MissionTypeFrontEndConfig

    MAPPING = {
        "item_id": "itemId",
        "help_title": "helpTitle",
        "help_description": "helpDescription",
        "long_description": "longDescription",
        "short_description": "shortDescription",
        "title": "title",
        "start_triggers": "startTriggers",
        "end_triggers": "endTriggers",
        "fail_triggers": "failTriggers",
        "rewards": "rewards",
    }

