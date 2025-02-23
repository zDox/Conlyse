from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class AdminState(GameObject):
    STATE_ID = 9