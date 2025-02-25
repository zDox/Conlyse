from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class GameEventState(GameObject):
    C = "ultshared.gameevents.UltGameEventState"
    STATE_ID = 24
    MAPPING = {}