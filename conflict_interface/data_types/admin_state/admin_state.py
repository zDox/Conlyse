from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class AdminState(State):
    C = "ultshared.UltAdminState"
    STATE_TYPE = 9
    MAPPING = {}