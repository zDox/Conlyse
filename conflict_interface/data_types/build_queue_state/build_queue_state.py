from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class BuildQueueState(State):
    C = "ultshared.UltBuildQueueState"
    STATE_TYPE = 19
    MAPPING = {}