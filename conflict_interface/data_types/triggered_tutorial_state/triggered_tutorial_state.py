from dataclasses import dataclass

from conflict_interface.data_types.state import State


@dataclass
class TriggeredTutorialState(State):
    C = "ultshared.UltTriggeredTutorialState"
    STATE_TYPE = 21
    MAPPING = {}