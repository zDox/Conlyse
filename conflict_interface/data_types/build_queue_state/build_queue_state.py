from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class BuildQueueState(GameObject):
    C = "ultshared.UltBuildQueueState"
    STATE_ID = 19
    MAPPING = {}