from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class BuildQueueState(GameObject):
    STATE_ID = 19