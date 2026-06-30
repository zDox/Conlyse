from dataclasses import dataclass
from typing import Optional

from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..mod_state.configuration import PremiumVisibilityConfig
from ..mod_state.configuration import TokenProducerConfig

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class Premium(GameObject):
    C = "ultshared.premium.UltPremium"
    item_id: Optional[int]
    max_quantity: int
    is_inventory_item: bool
    is_global_item: bool
    amount_factor: float
    name: str
    description: str
    visibility: PremiumVisibilityConfig
    token_producer_config: Optional[TokenProducerConfig]

    MAPPING = {
        "item_id": "itemID",
        "max_quantity": "maxQuantity",
        "is_inventory_item": "isInventoryItem",
        "is_global_item": "isGlobalItem",
        "amount_factor": "amountFactor",
        "name": "name",
        "description": "description",
        "visibility": "visibility",
        "token_producer_config": "tokenProducerConfig",
    }

