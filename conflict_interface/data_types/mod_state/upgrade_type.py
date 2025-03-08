from dataclasses import dataclass
from math import floor
from typing import List
from typing import Optional

from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.mod_state.configuration import ConflictCondition
from conflict_interface.data_types.mod_state.configuration import ConstructionSpeedupConfig
from conflict_interface.data_types.mod_state.configuration import FactorySpeedUpConfig
from conflict_interface.data_types.mod_state.configuration import HealArmiesUpgradeFeatureConfig
from conflict_interface.data_types.mod_state.configuration import UpgradeTypeFreeformConfig
from conflict_interface.data_types.mod_state.configuration import VictoryPointsGenerationConfig
from conflict_interface.data_types.mod_state.mod_state_enums import UpgradeFeature
from conflict_interface.data_types.mod_state.moddable_upgrade import ModableUpgrade
from conflict_interface.data_types.research_state.research_requirement_config import ResearchRequirementConfig


@dataclass
class UpgradeType(GameObject):
    C = "ut"
    id: int
    build_time: int # Wierd type of time format (only 5 digits)
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
    feature_functions: HashMap[int, int] # TODO type unknown
    build_time_functions: HashMap[int, int] # TODO type unknown
    replaced_upgrade: Optional[int]
    removed_upgrades: HashMap[int, ModableUpgrade] # TODO type unknown
    required_upgrades: HashMap[int, int]
    required_researches: HashMap[int, ResearchRequirementConfig] # TODO type unknown


    sorting_orders: str
    upgrade_identifier: str

    art: int # TODO Dont know what this is
    upgrade_description: str
    upgrade_name: str

    new_upgrade_description: HashMap[str,str]
    new_upgrade_name: HashMap[str,str]

    possible_province_states: HashMap[int, int]

    heal_armies_upgrade_feature_config: Optional[HealArmiesUpgradeFeatureConfig]
    construction_speedup_config: Optional[ConstructionSpeedupConfig]
    freeform_config: Optional[UpgradeTypeFreeformConfig]

    factory_speedup_config: Optional[FactorySpeedUpConfig]
    construction_requirement_config: ConflictCondition
    victory_points_generation_config: Optional[VictoryPointsGenerationConfig]

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
        "art": "art",
        "removed_upgrades": "rmu",
        "required_researches": "rqr",
        "feature_functions": "ff",
        "build_time_functions": "btf",
        "upgrade_description": "upd",
        "upgrade_name": "upn",
        "new_upgrade_description": "upgrDesc",
        "new_upgrade_name": "upgrName",
        "possible_province_states": "pps",
        "heal_armies_upgrade_feature_config": "hac",
        "construction_speedup_config": "csc",
        "freeform_config": "fc",
        "factory_speedup_config": "fsc",
        "construction_requirement_config": 'constructionRequirementConfig',
        "victory_points_generation_config": "victoryPointsGenerationConfig",

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
