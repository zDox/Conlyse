from dataclasses import dataclass

from .resource_category import ResourceCategory
from conflict_interface.utils import GameObject, HashMap
from conflict_interface.utils import ConMapping


def parse_categories(obj):
    if obj is None:
        return {}

    return {int(category_id): ResourceCategory.from_dict(category)
            for category_id, category in list(obj.items())[1:]}


@dataclass
class ResourceProfile(GameObject):
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
