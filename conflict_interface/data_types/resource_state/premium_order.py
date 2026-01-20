from dataclasses import dataclass

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable


@binary_serializable(SerializationCategory.DATACLASS)
@dataclass
class PremiumOrder(GameObject):
    C = "ultshared.UltPremiumOrder"
    order_id: int
    player_id: int
    resource_type: int
    amount: int
    limit: float
    buy: bool
    initial_amount: int
    initial_limit: float

    MAPPING = {
        "order_id": "orderID",
        "player_id": "playerID",
        "resource_type": "resourceType",
        "amount": "amount",
        "limit": "limit",
        "buy": "buy",
        "initial_amount": "initialAmount",
        "initial_limit": "initialLimit",
    }