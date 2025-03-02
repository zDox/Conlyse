from dataclasses import dataclass
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.state import State


@dataclass
class UserInventoryState(State):
    C = "ultshared.premium.UltUserInventory"
    STATE_TYPE = 16
    MAPPING = {}