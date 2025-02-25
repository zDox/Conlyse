from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class MissionState(GameObject):
    C = "ultshared.UltMissionState"
    STATE_ID = 29