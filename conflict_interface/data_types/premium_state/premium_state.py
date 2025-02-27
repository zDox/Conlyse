from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class PremiumState(GameObject):
    C = "ultshared.UltPremiumState"
    STATE_ID = 14
    MAPPING = {}