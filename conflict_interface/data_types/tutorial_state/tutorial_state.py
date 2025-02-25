from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class TutorialState(GameObject):
    C = "ultshared.UltTutorialState"
    STATE_ID = 18