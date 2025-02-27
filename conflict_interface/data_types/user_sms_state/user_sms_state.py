from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class UserSMSState(GameObject):
    C = "ultshared.UltUserSMSState"
    STATE_ID = 17
    MAPPING = {}