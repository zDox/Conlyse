from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class TutorialState(State):
    C = "ultshared.UltTutorialState"
    STATE_TYPE = 18
    MAPPING = {}