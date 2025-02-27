from dataclasses import dataclass

from .resource_category import ResourceCategory
from ..custom_types import HashMap
from ..game_object import GameObject, parse_any


def parse_categories(obj):
    if obj is None:
        return {}


    return {int(category_id): parse_any(ResourceCategory, category) for category_id, category in obj.items()}


@dataclass
class ResourceProfile(GameObject):
    C = "ultshared.UltResourceProfile"
    player_id: int
    # executed_orders
    # premium_orders
    # personal_orders
    categories: HashMap[int, ResourceCategory]
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
    }
