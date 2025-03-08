from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class StatisticState(State):
    C = "ultshared.UltStatisticState"
    STATE_TYPE = 10
    MAPPING = {}