from dataclasses import dataclass

from conflict_interface.data_types import GameObject, LinkedList
from conflict_interface.data_types.army_state.army import Army


@dataclass
class ArmyAction(GameObject):
    C = "ultshared.action.UltArmyAction"
    armies: LinkedList[Army]

    MAPPING = {
        "armies": "armies"
    }