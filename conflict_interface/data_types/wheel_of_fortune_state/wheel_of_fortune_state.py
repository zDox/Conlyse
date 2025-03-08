from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class WheelOfFortuneState(State):
    C = "ultshared.UltWheelOfFortuneState"
    STATE_TYPE = 22
    MAPPING = {}