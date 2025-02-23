from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class AIState(GameObject):
    STATE_ID = 13