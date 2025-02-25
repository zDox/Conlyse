from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class GameEventState(GameObject):
    C = "ultshared.GameEventState"
    STATE_ID = 24
