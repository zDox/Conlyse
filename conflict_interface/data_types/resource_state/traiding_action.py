from dataclasses import dataclass

from conflict_interface.data_types.action import Action
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable
from conflict_interface.data_types.resource_state.order import Order

@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class OrderAction(Action):
    C = "ultshared.action.UltOrderAction"
    order: Order
    cancel: bool

    MAPPING = {
        "order": "order",
        "cancel": "cancel"
    }

