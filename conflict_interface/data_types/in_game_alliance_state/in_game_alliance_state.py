from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class InGameAllianceState(GameObject):
    C = "ultshared.UltInGameAllianceState"
    STATE_ID = 25
    MAPPING = {}