from dataclasses import dataclass
from typing import Optional
from typing import Union

from conflict_interface.data_types.army_state.unit import Unit
from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.custom_types import ArraysArrayList
from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import HashSet
from conflict_interface.data_types.custom_types import TreeMap
from conflict_interface.data_types.map_state.map_state_enums import SeaType
from conflict_interface.data_types.map_state.map_state_enums import TerrainTypeStr
from conflict_interface.data_types.map_state.province_state import ProvinceState
from conflict_interface.data_types.mod_state.agression_level import AggressionLevel
from conflict_interface.data_types.mod_state.configuration import AStarConfig
from conflict_interface.data_types.mod_state.configuration import ArmyStackingPenaltyConfig
from conflict_interface.data_types.mod_state.configuration import FreeFormSoundConfig
from conflict_interface.data_types.mod_state.configuration import HealArmiesModFeatureConfig
from conflict_interface.data_types.mod_state.configuration import ModStateFrontendConfig
from conflict_interface.data_types.mod_state.configuration import MoraleBasedProductionConfig
from conflict_interface.data_types.mod_state.configuration import NewspaperConfig
from conflict_interface.data_types.mod_state.configuration import NoobBonusConfig
from conflict_interface.data_types.mod_state.configuration import PlayerProgressionConfig
from conflict_interface.data_types.mod_state.configuration import ReducedDamageArmorClassesConfig
from conflict_interface.data_types.mod_state.configuration import RenderConfig
from conflict_interface.data_types.mod_state.configuration import SoundConfig
from conflict_interface.data_types.mod_state.configuration import SpyConfig
from conflict_interface.data_types.mod_state.configuration import UberConfig
from conflict_interface.data_types.mod_state.mission_type import MissionType
from conflict_interface.data_types.mod_state.mod_state_enums import DamageType
from conflict_interface.data_types.mod_state.mod_state_enums import ModGameFeatures
from conflict_interface.data_types.mod_state.premium import Premium
from conflict_interface.data_types.mod_state.rank_cache import RankCache
from conflict_interface.data_types.mod_state.rank_type import RankType
from conflict_interface.data_types.mod_state.relation import Relation
from conflict_interface.data_types.mod_state.token_type import TokenType
from conflict_interface.data_types.mod_state.unit_type import UnitType
from conflict_interface.data_types.mod_state.upgrade_type import UpgradeType
from conflict_interface.data_types.research_state.research_type import ResearchType
from conflict_interface.data_types.resource_state.resource_entry import ResourceEntry
from conflict_interface.data_types.spy_state.premium_spy_job import CountryInfoJob
from conflict_interface.data_types.spy_state.premium_spy_job import DamageUpgradeJob
from conflict_interface.data_types.spy_state.premium_spy_job import DecreaseMoralJob
from conflict_interface.data_types.spy_state.premium_spy_job import DestroyResouceJob
from conflict_interface.data_types.spy_state.premium_spy_job import RevealAllArmiesJob
from conflict_interface.data_types.spy_state.premium_spy_job import RevealProvinceArmiesJob
from conflict_interface.data_types.spy_state.spy_mission import SpyMission
from conflict_interface.data_types.state import State
from conflict_interface.data_types.state import universal_update
from conflict_interface.replay.replay_patch import BidirectionalReplayPatch
from conflict_interface.replay.replay_patch import PathNode


@dataclass
class ModState(State):
    C = "ultshared.UltMod"
    STATE_TYPE = 11

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
    options: HashMap[ModGameFeatures, float]
    string_options: HashMap[str, str]
    premium_spy_jobs: ArrayList[Union[RevealProvinceArmiesJob, CountryInfoJob, DecreaseMoralJob, DestroyResouceJob, DamageUpgradeJob, RevealAllArmiesJob]]
    spy_missions: HashMap[int, SpyMission]
    premiums: HashMap[int, Premium]
    province_states: HashMap[int, ProvinceState]
    units: HashMap[int, Unit]
    terrain_types: TreeMap[int, TerrainTypeStr]
    sea_types: TreeMap[int, SeaType]
    damage_types: ArraysArrayList[DamageType]
    replacements: HashMap[int, HashSet[int]]
    has_admin_action: bool
    morale_based_construction_time_config: MoraleBasedProductionConfig
    morale_based_production_time_config: MoraleBasedProductionConfig
    heal_armies_mod_feature_config: HealArmiesModFeatureConfig
    reduced_damage_armor_classes_config: ReducedDamageArmorClassesConfig
    army_stacking_penalty_config: ArmyStackingPenaltyConfig
    astar_config: AStarConfig
    noob_bonus_config: NoobBonusConfig
    frontend_config: ModStateFrontendConfig
    rank_cache: Optional[RankCache]
    mission_types: HashMap[int, MissionType]
    token_types: HashMap[int, TokenType]
    rank_types: HashMap[int, RankType]
    spy_config: SpyConfig
    render_config: RenderConfig
    newspaper_config: NewspaperConfig
    sound_config: Union[SoundConfig,FreeFormSoundConfig]
    uber_config: UberConfig
    player_progress_config: PlayerProgressionConfig

    state_type: int  # should be the same as STATE_ID
    time_stamp: DateTimeMillisecondsInt
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
        "has_admin_action": "hasAdminAction",
        "morale_based_construction_time_config": "moraleBasedConstructionTimeConfig",
        "morale_based_production_time_config": "moraleBasedProductionTimeConfig",
        "heal_armies_mod_feature_config": "healArmiesModFeatureConfig",
        "reduced_damage_armor_classes_config": "reducedDamageArmorClassesConfig",
        "army_stacking_penalty_config": "armyStackingPenaltyConfig",
        "astar_config": "astarConfig",
        "noob_bonus_config": "noobBonusConfig",
        "frontend_config": "frontendConfig",
        "rank_cache": "rankCache",
        "mission_types": "missionTypes",
        "token_types": "tokenTypes",
        "rank_types": "rankTypes",
        "spy_config": "spyConfig",
        "render_config": "renderConfig",
        "newspaper_config": "newspaperConfig",
        "sound_config": "soundConfig",
        "uber_config": "uberConfig",
        "player_progress_config": "playerProgressionConfig",
    }

    def update(self, other: "State", path: list[PathNode] = None, rp: BidirectionalReplayPatch = None):
        universal_update(self, other, path, rp)

    def get_option(self, option: ModGameFeatures):
        return self.options.get(option, None)

    def get_transport_ship_id(self) -> int:
        return int(self.get_option(ModGameFeatures.OPTION_TRANSPORT_SHIP))