from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.resource_state.resource_types import ResourceType


@dataclass
class Order(GameObject):
    C = "ultshared.UltOrder"
    buy: bool
    amount: int
    limit: float
    player_id: int
    resourceType: ResourceType # TODO check if this is the right one
    order_id: int

    MAPPING = {
        "resourceType": "resourceType",
        "order_id": "orderID",
        "player_id": "playerID",
        "amount": "amount",
        "limit": "limit",
        "buy": "buy",
    }