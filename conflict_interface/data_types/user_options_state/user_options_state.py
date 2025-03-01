from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class UserOptionsState(State):
    C = "ultshared.UltUserOptions"
    STATE_TYPE = 15
    MAPPING = {}