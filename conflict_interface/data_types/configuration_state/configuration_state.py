
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class ConfigurationState(State):
    C = "ultshared.UltConfigurationState"
    STATE_TYPE = 28
    state_type: int = 28
    MAPPING = {}