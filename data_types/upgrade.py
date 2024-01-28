from data_types.utils import JsonMappedClass, MappedValue

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum


def parse_dict(obj):
    obj.pop("@c")
    return {int(key): value
            for key, value in obj.items()}


class UpgradeFeature(Enum):
    FORTRESS = 0,
    HARBOUR = 1,
    RAILROAD = 2,
    FACTORY = 3,
    CAPITAL = 4,
    MORALE_BONUS = 5,
    RECRUIT = 6,
    FACTORY_TECH = 7,
    AIRFIELD = 8,
    INDESTRUCTIBLE = 9,
    PUBLIC = 10,
    CONSTRUCTION_SLOTS = 12,
    PRODUCTION_SLOTS = 13,
    INVISIBLE = 14,
    NO_SPEED_UP = 15,
    INDESTRUCTABLE = 16,
    STATUS_CHANGE = 17,
    REPORT_PROGRESS = 18,
    VICTORY_POINTS = 19,
    SIEGE_DELAY = 20,
    MINIMUM_SIEGE = 21,
    RESEARCH_LIMIT_LEVEL = 23,
    MAX_MANPOWER = 24,
    STACKABLE = 25,
    SHOW_IN_NEWSPAPER = 26,
    BUILDING_PLOTS = 27,
    USED_BUILDING_PLOTS = 28,
    CAN_SPEEDUP_CONSTRUCTION = 31,
    CONSTRUCTION_CLASS = 32,
    CAN_HEAL_ARMIES = 34,
    DEMOLISHABLE = 38,
    NOT_ADDED_TO_PROVINCE = 39,
    INVISIBLE_FROM_STATS = 40


def parse_features(obj):
    obj.pop("@c")
    return {UpgradeFeature(key): value
            for key, value in obj.items()}


class ValueFunction(Enum):
    VALUE_FUNCTION_LINEAR = 0,
    VALUE_FUNCTION_SQRT = 1,
    VALUE_FUNCTION_PANZERWARS = 2,
    VALUE_FUNCTION_STEP = 3


@dataclass
class UpgradeType(JsonMappedClass):
    id: int
    build_time: timedelta
    build_condition: int
    max_condition: int
    min_condition: int
    day_of_availability: int
    enable_able: bool
    article_prefix: str
    costs: dict[int, int]
    unit_costs: dict[int, int]
    daily_costs: dict[int, int]
    daily_productions: dict[int, int]
    production_bonus: dict[int, float]
    features: dict[UpgradeFeature, float]
    # feature_functions -> Dont know how to implement
    # build_time_functions -> Dont know how to implement
    replaced_upgrade: int
    # removed_upgrades -> Dont know how to implement
    required_upgrades: dict[int, int]
    # required_researches -> Dont know how to implement
    feature_icon_prefix: str
    ranking_factor: int
    sorting_orders: int

    upgrade_identifier: str

    mapping = {
        "id": "id",
        "build_time": "bt",
        "build_condition": "bc",
        "max_condition": "mxc",
        "min_condition": "mnc",
        "day_of_availability": "doa",
        "enable_able": "ie",
        "article_prefix": "ap",
        "costs": MappedValue("c", parse_dict),
        "unit_costs": MappedValue("uc", parse_dict),
        "daily_costs": MappedValue("dc", parse_dict),
        "daily_productions": MappedValue("dp", parse_dict),
        "production_bonus": MappedValue("pb", parse_dict),
        "features": MappedValue("f", parse_features),
        "replaced_upgrade": "ru",
        "required_upgrades": MappedValue("rqu", parse_dict),
        "feature_icon_prefix": "fip",
        "ranking_factor": "rnf",
        "sorting_orders": "so",
        "upgrade_identifier": "uid",
    }
