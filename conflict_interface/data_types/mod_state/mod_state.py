from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from typing import Union

from conflict_interface.data_types.army_state.unit import Unit
from conflict_interface.data_types.map_state.province_state import ProvinceState
from conflict_interface.data_types.map_state.sea_type import SeaType
from conflict_interface.data_types.map_state.terrain_type import TerrainTypeStr
from conflict_interface.data_types.mod_state.configuration import AStarConfig
from conflict_interface.data_types.mod_state.configuration import ArmyStackingPenaltyConfig
from conflict_interface.data_types.mod_state.configuration import FrontendConfig
from conflict_interface.data_types.mod_state.configuration import HealArmiesModFeatureConfig
from conflict_interface.data_types.mod_state.configuration import MoraleBasedProductionConfig
from conflict_interface.data_types.mod_state.configuration import NoobBonusConfig
from conflict_interface.data_types.mod_state.configuration import ReducedDamageArmorClassesConfig
from conflict_interface.data_types.mod_state.damage_types import DamageType
from conflict_interface.data_types.mod_state.premium import Premium
from conflict_interface.data_types.research_state.research_type import ResearchType
from conflict_interface.data_types.resource_state.resource_entry import ResourceEntry
from conflict_interface.data_types.mod_state.agression_level import AggressionLevel
from conflict_interface.data_types.mod_state.relation import Relation
from conflict_interface.data_types.mod_state.unit_type import UnitType
from conflict_interface.data_types.custom_types import HashMap, HashSet, ArrayList, TreeMap
from conflict_interface.data_types.mod_state.upgrade_type import UpgradeType
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.spy_state.premium_spy_job import (CountryInfoJob, RevealProvinceArmiesJob,
                                                                     DecreaseMoralJob, DestroyResouceJob,
                                                                     DamageUpgradeJob, RevealAllArmiesJob)
from conflict_interface.data_types.spy_state.spy_mission import SpyMission


@dataclass
class ModState(GameObject):
    C = "ultshared.UltMod"
    STATE_ID = 11

    mod_id: int

    upgrades: HashMap[int, UpgradeType]
    unit_types: HashMap[int, UnitType]
    all_unit_types: HashMap[int, UnitType]

    relations: HashMap[int, Relation]
    aggression_levels: Optional[HashMap[int, AggressionLevel]]
    game_features: HashSet[int]
    resource_entries: HashMap[int, ResourceEntry]
    research_types: HashMap[int, ResearchType]
    resource_consumption: HashMap[int, int] # TODO it is a hashmap of what?
    options: HashMap[str, float]
    string_options: HashMap[str, str]
    premium_spy_jobs: ArrayList[Union[RevealProvinceArmiesJob, CountryInfoJob, DecreaseMoralJob, DestroyResouceJob, DamageUpgradeJob, RevealAllArmiesJob]]
    spy_missions: HashMap[int, SpyMission]
    premiums: HashMap[int, Premium]
    province_states: HashMap[int, ProvinceState]
    units: HashMap[int, Unit]
    terrain_types: TreeMap[int, TerrainTypeStr]
    sea_types: TreeMap[int, SeaType]
    damage_types: ArrayList[DamageType]
    replacements: HashMap[int, HashSet[int]]
    has_garrison: bool
    has_admin_action: bool
    morale_based_construction_time_config: MoraleBasedProductionConfig
    morale_based_production_time_config: MoraleBasedProductionConfig
    heal_armies_mod_feature_config: HealArmiesModFeatureConfig
    reduced_damage_armor_classes_config: ReducedDamageArmorClassesConfig
    army_stacking_penalty_config: ArmyStackingPenaltyConfig
    astar_config: AStarConfig
    noob_bonus_config: NoobBonusConfig
    frontend_config: FrontendConfig

    state_type: int  # should be the same as STATE_ID
    time_stamp: datetime
    state_id: str  # Is not the STATE_ID above

    # research_types: list(ResearchType)
    MAPPING = {
        "mod_id": "modID",
        "upgrades": "upgrades",
        "unit_types": "unitTypes",
        "state_type": "stateType",
        "time_stamp": "timeStamp",
        "state_id": "stateID",
        "all_unit_types": "allUnitTypes",
        "relations": "relations",
        "aggression_levels": "agressionLevels", # Lol they cant spell
        "game_features": "gameFeatures",
        "resource_entries": "resourceEntries",
        "research_types": "researchTypes",
        "resource_consumption": "resourceConsumption",
        "options": "options",
        "string_options": "stringOptions",
        "premium_spy_jobs": "premiumSpyJobs",
        "spy_missions": "spyMissions",
        "premiums": "premiums",
        "province_states": "provinceStates",
        "units": "units",
        "terrain_types": "terrainTypes",
        "sea_types": "seaTypes",
        "damage_types": "damageTypes",
        "replacements": "replacements",
        "has_garrison": "hasGarrison",
        "has_admin_action": "hasAdminAction",
        "morale_based_construction_time_config": "moraleBasedConstructionTimeConfig",
        "morale_based_production_time_config": "moraleBasedProductionTimeConfig",
        "heal_armies_mod_feature_config": "healArmiesModFeatureConfig",
        "reduced_damage_armor_classes_config": "reducedDamageArmorClassesConfig",
        "army_stacking_penalty_config": "armyStackingPenaltyConfig",
        "astar_config": "astarConfig",
        "noob_bonus_config": "noobBonusConfig",
        "frontend_config": "frontendConfig",
    }