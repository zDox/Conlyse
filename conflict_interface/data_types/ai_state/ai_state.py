from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class AIState(GameObject):
    """
    Holds information about the AI.

    Attributes:
        STATE_ID (int): The unique identifier for the AI state.

    TODO:
        * Implement AI state.
    """
    C = "ultshared.UltAIState"
    STATE_ID = 13
    MAPPING = {}