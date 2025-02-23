from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class MissionState(GameObject):
    STATE_ID = 29