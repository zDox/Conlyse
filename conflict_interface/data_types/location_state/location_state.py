from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class LocationState(State):
    C = "ultshared.UltLocationState"
    STATE_TYPE = 20
    MAPPING = {}