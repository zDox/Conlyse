from dataclasses import dataclass


from ..state import State
from ..update_helpers import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.constants import PathNode
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable


from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class AIState(State):
    """
    Holds information about the AI.

    Attributes:
        STATE_TYPE (int): The unique identifier for the AI state.

    TODO:
        * Implement AI state.
    """
    C = "ultshared.UltAIState"
    STATE_TYPE = 13
    MAPPING = {}

    def update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        state_update(self, other, path, rp)