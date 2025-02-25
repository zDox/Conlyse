from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class AdminState(GameObject):
    C = "ultshared.UltAdminState"
    STATE_ID = 9

    MAPPING = {}