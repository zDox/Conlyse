from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class MapInfoState(State):
    C = "ultshared.UltMapInfoState"
    STATE_TYPE = 8
    MAPPING = {}