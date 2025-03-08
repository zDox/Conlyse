from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class MissionState(State):
    C = "ultshared.gamestates.UltMissionState"
    STATE_TYPE = 29
    MAPPING = {}