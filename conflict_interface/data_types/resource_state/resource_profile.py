from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.resource_state.resource_types import ResourceType
from conflict_interface.data_types.custom_types import LinkedList, HashMap, ArrayList
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.resource_state.order import Order
from conflict_interface.data_types.resource_state.premium_order import PremiumOrder
from conflict_interface.data_types.resource_state.resource_category import ResourceCategory
from conflict_interface.data_types.game_object import parse_any


def parse_categories(obj):
    if obj is None:
        return {}


    return {int(category_id): parse_any(ResourceCategory, category) for category_id, category in obj.items()}


@dataclass
class ResourceProfile(GameObject):
    C = "ultshared.UltResourceProfile"
    player_id: int
    executed_orders: LinkedList[Order] # TODO check if this are actually orders
    premium_orders: Optional[HashMap[int, PremiumOrder]]
    personal_orders: Optional[HashMap[int, ArrayList[Order]]]
    categories: Optional[HashMap[int, ResourceCategory]]
    mobilization_target: int
    mobilization_value: int
    corruption_value: float
    damage_sensitive_morale_penalty: float

    MAPPING = {
        "player_id": "playerID",
        "categories": "categories",
        "mobilization_target": "mobilizationTarget",
        "mobilization_value": "mobilizationValue",
        "corruption_value": "corruptionValue",
        "damage_sensitive_morale_penalty": "damageSensitiveMoralePenalty",
        "executed_orders": "executedOrders",
        "premium_orders": "premiumOrders",
        "personal_orders": "personalOrders",
    }
