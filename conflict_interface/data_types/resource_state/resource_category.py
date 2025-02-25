from dataclasses import dataclass

from .resource_entry import ResourceEntry
from ..custom_types import HashMap
from ..game_object import GameObject, parse_any


def parse_resource_entries(obj):
    if obj is None:
        return {}

    return {int(resource_id): parse_any(ResourceEntry, resource) for resource_id, resource in obj.items()}


@dataclass
class ResourceCategory(GameObject):
    C = "ultshared.UltResourceCategory"
    category_id: int
    name: str
    daily_unit_consumption: float
    daily_upgrade_consumption: float
    daily_population_consumption: float
    min_consumption: float
    resources: HashMap[int, ResourceEntry]

    MAPPING = {
        "category_id": "categoryID",
        "name": "name",
        "daily_unit_consumption": "dailyUnitConsumption",
        "daily_upgrade_consumption": "dailyUpgradeConsumption",
        "daily_population_consumption": "dailyPopulationConsumption",
        "min_consumption": "minConsumption",
        "resources": "resourceEntries",
    }
