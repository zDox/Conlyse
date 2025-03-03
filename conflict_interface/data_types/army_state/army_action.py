from dataclasses import dataclass

from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.action import Action
from conflict_interface.data_types.army_state.army import Army


@dataclass
class ArmyAction(Action):
    C = "ultshared.action.UltArmyAction"
    armies: LinkedList[Army]

    MAPPING = {
        "armies": "armies",
    }