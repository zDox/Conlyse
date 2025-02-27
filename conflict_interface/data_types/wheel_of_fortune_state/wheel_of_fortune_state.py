from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class WheelOfFortuneState(GameObject):
    C = "ultshared.UltWheelOfFortuneState"
    STATE_ID = 22
    MAPPING = {}