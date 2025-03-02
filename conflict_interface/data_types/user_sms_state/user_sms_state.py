from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class UserSMSState(State):
    C = "ultshared.UltUserSMSState"
    STATE_TYPE = 17
    MAPPING = {}