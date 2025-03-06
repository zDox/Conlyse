from dataclasses import dataclass
from math import floor

from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.resource_state.resource_types import ResourceType



@dataclass
class ResourceEntry(GameObject):
    C = "re"
    resource_id: ResourceType
    name: str

    daily_unit_consumption: float
    daily_upgrade_consumption: float
    daily_population_consumption: float
    min_consumption: float

    updating: bool
    priority: float
    production: float

    amount_zero: float
    time_zero: DateTimeMillisecondsInt
    rate: float  # in unit per second
    lack_zero: float
    consumed_zero: float
    produced_zero: float

    available_for_premium: bool
    include_in_statistics: bool
    min_price: int
    max_price: int

    manpower: bool
    currency: bool

    production_factor: float = 1
    consumption_factor: float = 1

    min_amount: float = 0
    max_amount: float = 0
    tradable: bool = False

    MAPPING = {
        "resource_id": "resourceID",
        "name": "name",
        "daily_unit_consumption": "dailyUnitConsumption",
        "daily_upgrade_consumption": "dailyUpgradeConsumption",
        "daily_population_consumption": "dailyPopulationConsumption",
        "min_consumption": "minConsumption",
        "updating": "updating",
        "priority": "priority",
        "production": "production",
        "min_amount": "minimumAmount",
        "max_amount": "maxAmount",
        "amount_zero": "amount0",
        "time_zero": "time0",
        "rate": "rate",
        "lack_zero": "lack0",
        "consumed_zero": "consumed0",
        "produced_zero": "produced0",
        "available_for_premium": "availableForPremium",
        "include_in_statistics": "includeInStatistics",
        "min_price": "minPrice",
        "max_price": "maxPrice",
        "tradable": "tradable",
        "manpower": "manpower",
        "currency": "currency",
        "production_factor": "productionFactor",
        "consumption_factor": "consumptionFactor"
    }

    def get_resource_amount(self) -> int:
        delta = self.game.client_time() - self.time_zero
        return floor(self.amount_zero + delta.total_seconds() * self.rate)
