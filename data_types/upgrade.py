from data_types.utils import JsonMappedClass, MappedValue

from dataclasses import dataclass
from datetime import timedelta


def parse_dict(obj):
    obj.pop("@c")
    return {int(key): value
            for key, value in obj.items()}


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
    features: dict[int, float]
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
        "features": MappedValue("f", parse_dict),
        "replaced_upgrade": "ru",
        "required_upgrades": MappedValue("rqu", parse_dict),
        "feature_icon_prefix": "fip",
        "ranking_factor": "rnf",
        "sorting_orders": "so",
        "upgrade_identifier": "uid",
    }
