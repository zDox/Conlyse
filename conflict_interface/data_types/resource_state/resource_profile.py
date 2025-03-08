from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import LinkedList
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.resource_state.order import Order
from conflict_interface.data_types.resource_state.premium_order import PremiumOrder
from conflict_interface.data_types.resource_state.resource_category import ResourceCategory
from conflict_interface.data_types.resource_state.resource_state_enums import ResourceType


@dataclass
class ResourceProfile(GameObject):
    C = "ultshared.UltResourceProfile"
    player_id: int
    executed_orders: LinkedList[Order] # TODO check if this are actually orders
    premium_orders: Optional[HashMap[int, PremiumOrder]]
    personal_orders: Optional[HashMap[int, ArrayList[Order]]]
    categories: HashMap[int, ResourceCategory]
    mobilization_target: int
    mobilization_value: int
    corruption_value: float
    damage_sensitive_morale_penalty: float

    _resource_type_to_category: dict[ResourceType, ResourceCategory] = None

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

    def get_resource_amounts(self) -> dict[ResourceType, int]:
        """
        Computes the current amount of each resource type.
        Returns them in a dictionary.

        Returns:
            dict[ResourceType, int]: A dictionary mapping each resource
            type to its amount.
        """
        amounts = {}
        for category in self.categories.values():
            for resource_type, resource_entry in category.resources.items():
                amounts[resource_type] = resource_entry.get_resource_amount()
        return amounts

    def is_affordable(self, cost: dict[ResourceType, int]) -> bool:
        """
        Determines if the cost of resources can be afforded given the current
        available resources.

        This method checks if the available quantities of resources, obtained
        by calling `get_resource_amounts`, are sufficient to meet the specified
        cost requirements for each type of resource.

        Parameters:
            cost: dict[ResourceType, int]
                A dictionary representing the cost of resources where the key
                is the resource type and the value is the required amount.

        Returns:
            bool: Returns True if the available resources are sufficient to cover
                the cost; otherwise, returns False.
        """
        resource_amounts = self.get_resource_amounts()
        for resource_type, amount in cost.items():
            if resource_amounts[resource_type] < amount:
                return False
        return True

    def get_resource_entry(self, resource_type: ResourceType) -> Optional[ResourceCategory]:
        if not self._resource_type_to_category:
            for category in self.categories.values():
                for entry in category.resources.items():
                    self._resource_type_to_category[entry[0]] = category
        resource_category = self._resource_type_to_category.get(resource_type)
        if resource_category:
            return resource_category.resources.get(resource_type)
        else:
            return None