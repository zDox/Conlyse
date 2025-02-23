from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from math import floor
from typing import List, Optional

from conflict_interface.utils import GameObject, Point, HashMap


class UpgradeFeature(Enum):
    FORTRESS = 0
    HARBOUR = 1
    RAILROAD = 2
    FACTORY = 3
    CAPITAL = 4
    MORALE_BONUS = 5
    RECRUIT = 6
    FACTORY_TECH = 7
    AIRFIELD = 8
    INDESTRUCTIBLE = 9
    PUBLIC = 10
    UNKNOWN_11 = 11  # Not known what this feature does
    CONSTRUCTION_SLOTS = 12
    PRODUCTION_SLOTS = 13
    INVISIBLE = 14
    NO_SPEED_UP = 15
    INDESTRUCTABLE = 16
    STATUS_CHANGE = 17
    REPORT_PROGRESS = 18
    VICTORY_POINTS = 19
    SIEGE_DELAY = 20
    MINIMUM_SIEGE = 21
    UNKNOWN_22 = 22  # Not known what this feature does
    RESEARCH_LIMIT_LEVEL = 23
    MAX_MANPOWER = 24
    STACKABLE = 25
    SHOW_IN_NEWSPAPER = 26
    BUILDING_PLOTS = 27
    USED_BUILDING_PLOTS = 28
    UNKNOWN_29 = 29  # Not known what this feature does
    UNKNOWN_30 = 30  # Not known what this feature does
    CAN_SPEEDUP_CONSTRUCTION = 31
    CONSTRUCTION_CLASS = 32
    UNKNOWN_33 = 33  # Not known what this feature does
    CAN_HEAL_ARMIES = 34
    UNKNOWN_35 = 35  # Not known what this feature does
    UNKNOWN_36 = 36  # Not known what this feature does
    UNKNOWN_37 = 37  # Not known what this feature does
    DEMOLISHABLE = 38
    NOT_ADDED_TO_PROVINCE = 39
    INVISIBLE_FROM_STATS = 40


def parse_features(obj):
    obj.pop("@c")
    return {UpgradeFeature(int(key)): value
            for key, value in obj.items()}


class ValueFunction(Enum):
    VALUE_FUNCTION_LINEAR = 0,
    VALUE_FUNCTION_SQRT = 1,
    VALUE_FUNCTION_PANZERWARS = 2,
    VALUE_FUNCTION_STEP = 3


@dataclass
class UpgradeType(GameObject):
    id: int
    build_time: timedelta
    build_condition: int
    max_condition: int
    min_condition: int

    article_prefix: str
    costs: HashMap[int, int]
    unit_costs: HashMap[int, int]
    daily_costs: HashMap[int, int]
    daily_productions: HashMap[int, int]
    production_bonus: HashMap[int, float]
    features: HashMap[UpgradeFeature, float]
    # feature_functions -> Dont know how to implement
    # build_time_functions -> Dont know how to implement
    replaced_upgrade: Optional[int]
    # removed_upgrades -> Dont know how to implement
    required_upgrades: HashMap[int, int]
    # required_researches -> Dont know how to implement


    sorting_orders: int
    upgrade_identifier: str

    ranking_factor: int = 1
    feature_icon_prefix: str = ""
    enable_able: bool = False
    day_of_availability: int = 0

    _tier: int | None = None
    _replacing_upgrade_id: int | None = None

    MAPPING = {
        "id": "id",
        "build_time": "bt",
        "build_condition": "bc",
        "max_condition": "mxc",
        "min_condition": "mnc",
        "day_of_availability": "doa",
        "enable_able": "ie",
        "article_prefix": "ap",
        "costs": "c",
        "unit_costs": "uc",
        "daily_costs": "dc",
        "daily_productions": "dp",
        "production_bonus": "pb",
        "features": "f",
        "replaced_upgrade": "ru",
        "required_upgrades": "rqu",
        "feature_icon_prefix": "fip",
        "ranking_factor": "rnf",
        "sorting_orders": "so",
        "upgrade_identifier": "uid",
    }

    def has_feature(self, feature: UpgradeFeature):
        return feature in self.features.keys()

    def get_build_condition(self) -> int:
        return self.build_condition

    def get_max_condition(self) -> int:
        return self.max_condition

    def get_max_level(self) -> int:
        """
        Get the maximum level of the upgrade based on its conditions.
        """
        return self.max_condition // self.build_condition

    def get_level(self, condition: int) -> int:
        """
        Calculate the level of the upgrade using the condition.
        """
        return 1 + floor((condition - 1) / self.build_condition) if condition > 0 else 1

    def get_condition_for_level(self, level: int) -> int:
        """
        Get the condition value needed for a specific level.
        """
        return min(level * self.build_condition, self.get_max_condition())

    def get_min_condition(self) -> int:
        return self.min_condition

    def get_replaced_upgrade(self) -> int:
        return self.replaced_upgrade

    def get_removed_upgrades(self) -> List[int]:
        """
        Get a list of upgrades that this upgrade removes.
        """
        return list(self.removed_upgrades)

    @property
    def tier(self) -> int:
        """
        Calculate and return the tier of the upgrade.
        """
        if self._tier is None:
            replaced_upgrade_id = self.get_replaced_upgrade()
            if replaced_upgrade_id is not None:
                replaced_upgrade = self.game.get_upgrade_type(replaced_upgrade_id)  # Retrieve the replaced upgrade object
                self._tier = replaced_upgrade.tier + self.get_max_level()
            else:
                self._tier = self.get_max_level()
        return self._tier

    def get_max_tier(self) -> int:
        """
        Get the maximum tier of this or related upgrades iteratively.
        """
        last_replacing_upgrade_id = self.get_last_replacing_upgrade()
        if last_replacing_upgrade_id:
            last_replacing_upgrade = self.game.get_upgrade_type(last_replacing_upgrade_id)
            return last_replacing_upgrade.tier
        return self.tier

    def get_last_replacing_upgrade(self) -> int:
        """
        Get the last replacing upgrade of this upgrade, if any.
        """
        replacing_upgrade = None
        replacing_id = self._replacing_upgrade_id or 0
        while replacing_id > 0:
            replacing_upgrade = self.game.get_upgrade_type(replacing_id)
            replacing_id = replacing_upgrade.get_replacing_upgrade()
        return replacing_upgrade.id if replacing_upgrade else 0

    def get_replacing_upgrade(self) -> int:
        """
        Find an upgrade that replaces this one.
        """
        if not self._replacing_upgrade_id:
            upgrades = self.game.get_upgrade_types()
            self._replacing_upgrade_id = 0
            for upgrade_id, upgrade in upgrades.items():
                if upgrade.get_replaced_upgrade() == self.id:
                    self._replacing_upgrade_id = upgrade_id
                    break
        return self._replacing_upgrade_id


@dataclass
class ModableUpgrade(GameObject):
    id: int
    condition: Optional[int]

    relative_position: Optional[Point]
    enabled: bool = True
    premium_level: int = 0
    constructing: bool = False
    C = "mu"
    MAPPING = {
        "id": "id",
        "condition": "c",
        "constructing": "cn",
        "enabled": "e",
        "relative_position": "rp",
        "premium_level": "pl",
    }

    def __hash__(self):
        return hash((self.id, self.condition, self.relative_position, self.enabled, self.premium_level, self.constructing))
