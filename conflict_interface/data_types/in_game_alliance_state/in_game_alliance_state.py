from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class InGameAllianceState(GameObject):
    STATE_ID = 25