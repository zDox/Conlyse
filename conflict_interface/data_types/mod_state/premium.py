from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject


@dataclass
class Premium(GameObject):
    C = "ultshared.premium.UltPremium"
    item_id: Optional[int]
    max_quantity: int
    is_inventory_item: bool
    is_global_item: bool
    amount_factor: float # TODO check int
    name: str
    description: str

    MAPPING = {
        "item_id": "itemID",
        "max_quantity": "maxQuantity",
        "is_inventory_item": "isInventoryItem",
        "is_global_item": "isGlobalItem",
        "amount_factor": "amountFactor",
        "name": "name",
        "description": "description",
    }

