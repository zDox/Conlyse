from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class MapInfoState(GameObject):
    STATE_ID = 8