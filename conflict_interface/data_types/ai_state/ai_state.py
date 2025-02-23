from dataclasses import dataclass

from conflict_interface.utils import GameObject

@dataclass
class AIState(GameObject):
    """
    Holds information about the AI.

    Attributes:
        STATE_ID (int): The unique identifier for the AI state.

    TODO:
        * Implement AI state.
    """
    STATE_ID = 13