from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class ExplorationState(GameObject):
    STATE_ID = 26