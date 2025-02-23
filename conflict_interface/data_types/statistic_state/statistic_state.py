from dataclasses import dataclass

from conflict_interface.utils import GameObject


@dataclass
class StatisticState(GameObject):
    STATE_ID = 10