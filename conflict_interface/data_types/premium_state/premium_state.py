from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class PremiumState(State):
    C = "ultshared.UltPremiumState"
    STATE_TYPE = 14
    MAPPING = {}