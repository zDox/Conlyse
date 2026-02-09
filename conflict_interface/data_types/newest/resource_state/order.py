from dataclasses import dataclass
from typing import Optional

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.data_types.resource_state.resource_state_enums import ResourceType

from conflict_interface.data_types.version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class Order(GameObject):
    C = "ultshared.UltOrder"
    buy: bool
    amount: int
    limit: float
    player_id: int
    embargo: Optional[bool]
    resource_type: ResourceType  # TODO check if this is the right one

    total_price: Optional[str]
    icon: Optional[str]
    icon_small: Optional[str]
    order_id: Optional[int]
    is_owner: Optional[bool]

    MAPPING = {
        "resource_type": "resourceType",
        "order_id": "orderID",
        "player_id": "playerID",
        "amount": "amount",
        "limit": "limit",
        "buy": "buy",
        "embargo": "embargo",
        "total_price": "totalPrice",
        "icon": "icon",
        "icon_small": "iconSmall",
        "is_owner": "isOwner"
    }