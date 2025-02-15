from conflict_interface.utils import GameObject
from dataclasses import dataclass

@dataclass
class SpyState(GameObject):
    STATE_ID = 7
    # Spies, Nations, SpyReports
