from dataclasses import dataclass

from ..action import Action
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..resource_state.order import Order

from ..version import VERSION
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

