from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


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