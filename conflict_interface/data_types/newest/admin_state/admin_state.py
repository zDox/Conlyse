from dataclasses import dataclass

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.data_types.state import State
from conflict_interface.data_types.update_helpers import state_update
from conflict_interface.data_types.version import VERSION
from conflict_interface.replay.constants import PathNode


@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class AdminState(State):
    C = "ultshared.UltAdminState"
    STATE_TYPE = 9
    MAPPING = {}

    def update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        state_update(self, other, path, rp)