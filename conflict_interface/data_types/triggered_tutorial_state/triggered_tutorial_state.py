from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject


@dataclass
class TriggeredTutorialState(GameObject):
    C = "ultshared.UltTriggeredTutorialState"
    STATE_ID = 21