from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class LocationState(GameObject):
    C = "ultshared.UltLocationState"
    STATE_ID = 20
    MAPPING = {}