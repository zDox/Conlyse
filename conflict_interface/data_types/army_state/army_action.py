from dataclasses import dataclass

from conflict_interface.data_types import GameObject, LinkedList
from conflict_interface.data_types.army_state.army import Army


@dataclass
class ArmyAction(GameObject):
    C = "ultshared.action.UltArmyAction"
    armies: LinkedList[Army]
    action_request_id: str
    language: str

    MAPPING = {
        "armies": "armies",
        "action_request_id": "requestID",
        "language": "language"
    }