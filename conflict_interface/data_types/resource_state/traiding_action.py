from dataclasses import dataclass

from conflict_interface.data_types.action import Action
from conflict_interface.data_types.resource_state.order import Order


@dataclass
class OrderAction(Action):
    C = "ultshared.action.UltOrderAction"
    order: Order
    cancel: bool

    MAPPING = {
        "order": "order",
        "cancel": "cancel"
    }

