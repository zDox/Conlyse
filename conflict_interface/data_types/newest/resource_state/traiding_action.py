from dataclasses import dataclass

from conflict_interface.data_types.action import Action
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.data_types.resource_state.order import Order

from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class OrderAction(Action):
    C = "ultshared.action.UltOrderAction"
    order: Order
    cancel: bool

    MAPPING = {
        "order": "order",
        "cancel": "cancel"
    }

