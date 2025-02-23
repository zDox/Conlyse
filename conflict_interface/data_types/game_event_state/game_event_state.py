from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class GameEventState(GameObject):
    STATE_ID = 24
