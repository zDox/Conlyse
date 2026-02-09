from dataclasses import dataclass

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..state import State
from ..update_helpers import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode


@conflict_serializable(SerializationCategory.DATACLASS)
@dataclass
class ConfigurationState(State):
    C = "ultshared.UltConfigurationState"
    STATE_TYPE = 28
    state_type: int = 28
    MAPPING = {}

    def update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        state_update(self, other, path, rp)