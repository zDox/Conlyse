from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class GameEventState(State):
    C = "ultshared.gameevents.UltGameEventState"
    STATE_TYPE = 24
    MAPPING = {}