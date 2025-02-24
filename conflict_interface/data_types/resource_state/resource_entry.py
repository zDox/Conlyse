from dataclasses import dataclass
from datetime import datetime

from conflict_interface.data_types.resource_state.resource_types import ResourceType
from conflict_interface.utils import GameObject


@dataclass
class ResourceEntry(GameObject):
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
    time_zero: datetime
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

    min_amount: float = 0
    max_amount: float = 0
    tradeable: bool = False

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
        "tradeable": "tradeable",
        "manpower": "manpower",
        "currency": "currency",
    }

    def get_resource_amount(self) -> float:
        delta = int(self.game.get_latest_uptime().timestamp() / 1000) - int(self.time_zero.timestamp() / 1000)
        return self.amount_zero + delta * 1000 * self.rate
