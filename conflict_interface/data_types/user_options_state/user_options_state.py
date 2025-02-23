from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class UserOptionsState(GameObject):
    STATE_ID = 15