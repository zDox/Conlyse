from data_types.utils import JsonMappedClass, MappedValue

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ResourceEntry(JsonMappedClass):
    resource_id: int
    name: str

    daily_unit_consumption: float
    daily_upgrade_consumption: float
    daily_population_consumption: float
    min_consumption: float

    updating: bool
    priority: float
    production: float
    min_amount: float
    max_amount: float

    amount_zero: float
    time_zero: datetime
    rate: float
    lack_zero: float
    consumed_zero: float
    produced_zero: float

    available_for_premium: bool
    include_in_statistics: bool
    min_price: int
    max_price: int
    tradable: bool
    manpower: bool
    currency: bool

    mapping = {
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
    }


def parse_resource_entries(obj):
    if obj is None:
        return {}
    return {int(resource_id): ResourceEntry.from_dict(resource)
            for resource_id, resource in list(obj.items())[1:]}


@dataclass
class ResourceCategory(JsonMappedClass):
    catergory_id: int
    name: str
    daily_unit_consumption: float
    daily_upgrade_consumption: float
    daily_population_consumption: float
    min_consumption: float
    resource_entries: dict[int, ResourceEntry]

    mapping = {
        "catergory_id": "categoryID",
        "name": "name",
        "daily_unit_consumption": "dailyUnitConsumption",
        "daily_upgrade_consumption": "dailyUpgradeConsumption",
        "daily_population_consumption": "dailyPopulationConsumption",
        "min_consumption": "minConsumption",
        "resource_entries": MappedValue("resourceEntries",
                                        parse_resource_entries),
    }


def parse_categories(obj):
    if obj is None:
        return {}

    return {int(category_id): ResourceCategory.from_dict(category)
            for category_id, category in list(obj.items())[1:]}


@dataclass
class ResourceProfile(JsonMappedClass):
    player_id: int
    # executed_orders
    # premium_orders
    # personal_orders
    categories: ResourceCategory
    mobilization_target: int
    mobilization_value: int
    corruption_value: float
    damage_sensitive_morale_penalty: float

    mapping = {
        "player_id": "playerID",
        "categories": MappedValue("categories", parse_categories),
        "mobilization_target": "mobilizationTarget",
        "mobilization_value": "mobilizationValue",
        "corruption_value": "corruptionValue",
        "damage_sensitive_morale_penalty": "damageSensitiveMoralePenalty",
    }
