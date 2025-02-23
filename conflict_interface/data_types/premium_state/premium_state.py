from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class PremiumState(GameObject):
    STATE_ID = 14