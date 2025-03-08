from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class InGameAllianceState(State):
    C = "ultshared.UltInGameAllianceState"
    STATE_TYPE = 25
    MAPPING = {}