from dataclasses import dataclass

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import binary_serializable


from conflict_interface.data_types.version import VERSION
@binary_serializable(SerializationCategory.DATACLASS, version = VERSION)
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