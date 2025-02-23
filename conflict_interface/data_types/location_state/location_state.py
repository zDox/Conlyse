from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class LocationState(GameObject):
    STATE_ID = 20