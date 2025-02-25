from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class UserOptionsState(GameObject):
    C = "ultshared.UltUserOptions"
    STATE_ID = 15
    MAPPING = {}