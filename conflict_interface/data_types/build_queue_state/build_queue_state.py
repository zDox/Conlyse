from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class BuildQueueState(GameObject):
    C = "ultshared.BuildQueueState"
    STATE_ID = 19