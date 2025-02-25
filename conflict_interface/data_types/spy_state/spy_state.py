from conflict_interface.data_types.game_object import GameObject
from dataclasses import dataclass

@dataclass
class SpyState(GameObject):
    C = "ultshared.UltSpyState"
    STATE_ID = 7
    # Spies, Nations, SpyReports
