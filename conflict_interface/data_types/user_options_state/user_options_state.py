from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class UserOptionsState(GameObject):
    C = "ultshared.UltUserOptionsState"
    STATE_ID = 15