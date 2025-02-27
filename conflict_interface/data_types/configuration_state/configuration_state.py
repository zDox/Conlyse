
from conflict_interface.data_types.game_object import GameObject

from dataclasses import dataclass

@dataclass
class ConfigurationState(GameObject):
    C = "ultshared.UltConfigurationState"
    STATE_ID = 28
    MAPPING = {}