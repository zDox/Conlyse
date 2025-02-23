from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class WheelOfFortuneState(GameObject):
    STATE_ID = 22