from dataclasses import dataclass

from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable
from conflict_interface.data_types.state import State
from conflict_interface.data_types.update_helpers import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class ExplorationState(State):
    C = "ultshared.ExplorationState"
    STATE_TYPE = 26
    MAPPING = {}

    def update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        state_update(self, other, path, rp)