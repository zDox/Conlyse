from dataclasses import dataclass

from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..state import State
from ..update_helpers import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode


from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TriggeredTutorialState(State):
    C = "ultshared.UltTriggeredTutorialState"
    STATE_TYPE = 21
    MAPPING = {}

    def update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        state_update(self, other, path, rp)