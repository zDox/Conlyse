from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class MapInfoState(GameObject):
    C = "ultshared.UltMapInfoState"
    STATE_ID = 8