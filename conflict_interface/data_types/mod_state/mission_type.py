from dataclasses import dataclass

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable
from conflict_interface.data_types.mod_state.configuration import MissionTypeFrontEndConfig
from conflict_interface.data_types.mod_state.mission_reward import MissionReward
from conflict_interface.data_types.mod_state.mission_trigger import MissionTrigger

from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class MissionType(GameObject):
    C = "ultshared.modding.types.UltMissionType"
    item_id: int
    help_title: str
    help_description: str
    long_description: str
    short_description: str
    title: str
    start_triggers: ArrayList[MissionTrigger] #TODO check typing
    end_triggers: ArrayList[MissionTrigger]
    fail_triggers: ArrayList[MissionTrigger] #TODO check typing

    rewards: ArrayList[MissionReward]
    frontend_config: MissionTypeFrontEndConfig

    MAPPING = {
        "item_id": "itemID",
        "help_title": "helpTitle",
        "help_description": "helpDescription",
        "long_description": "longDescription",
        "short_description": "shortDescription",
        "title": "title",
        "start_triggers": "startTriggers",
        "end_triggers": "endTriggers",
        "fail_triggers": "failTriggers",
        "rewards": "rewards",
        "frontend_config": "frontendConfig",
    }

