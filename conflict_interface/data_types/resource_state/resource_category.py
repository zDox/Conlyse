from dataclasses import dataclass

from conflict_interface.data_types.resource_state.resource_types import ResourceType
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.resource_state.resource_entry import ResourceEntry
from conflict_interface.data_types.game_object import parse_any


@dataclass
class ResourceCategory(GameObject):
    C = "rc"
    category_id: int
    name: str
    daily_unit_consumption: float
    daily_upgrade_consumption: float
    daily_population_consumption: float
    min_consumption: float
    resources: HashMap[ResourceType, ResourceEntry]

    MAPPING = {
        "category_id": "categoryID",
        "name": "name",
        "daily_unit_consumption": "dailyUnitConsumption",
        "daily_upgrade_consumption": "dailyUpgradeConsumption",
        "daily_population_consumption": "dailyPopulationConsumption",
        "min_consumption": "minConsumption",
        "resources": "resourceEntries",
    }

    def get_resource_entry(self, resource_id: ResourceType) -> ResourceEntry:
        return self.resources[resource_id]