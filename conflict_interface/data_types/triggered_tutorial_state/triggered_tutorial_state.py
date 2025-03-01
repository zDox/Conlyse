from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class TriggeredTutorialState(State):
    C = "ultshared.UltTriggeredTutorialState"
    STATE_TYPE = 21
    MAPPING = {}