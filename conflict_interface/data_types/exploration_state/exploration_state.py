from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class ExplorationState(GameObject):
    C = "ultshared.ExplorationState"
    STATE_ID = 26