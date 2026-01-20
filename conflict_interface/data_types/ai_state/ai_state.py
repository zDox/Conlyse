from dataclasses import dataclass


from conflict_interface.data_types.state import State
from conflict_interface.data_types.state import state_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
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