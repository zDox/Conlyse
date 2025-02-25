from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class StatisticState(GameObject):
    C = "ultshared.UltStatisticState"
    STATE_ID = 10