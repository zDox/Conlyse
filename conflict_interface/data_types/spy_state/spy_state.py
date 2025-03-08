from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class SpyState(State):
    C = "ultshared.UltSpyState"
    STATE_TYPE = 7
    # Spies, Nations, SpyReports
    MAPPING = {}
