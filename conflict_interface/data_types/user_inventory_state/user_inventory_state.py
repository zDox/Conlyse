from dataclasses import dataclass
from conflict_interface.data_types.game_object import GameObject


@dataclass
class UserInventoryState(GameObject):
    C = "ultshared.UltUserInventoryState"
    STATE_ID = 16