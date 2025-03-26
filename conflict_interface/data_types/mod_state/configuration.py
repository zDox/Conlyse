from dataclasses import dataclass
from threading import Condition
from typing import Any
from typing import Optional
from typing import Union

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import EmptyList
from conflict_interface.data_types.custom_types import EmptyMap
from conflict_interface.data_types.custom_types import RegularImmutableMap
from conflict_interface.data_types.constant_segment_function import ConstantSegmentFunction
from conflict_interface.data_types.custom_types import TimeDeltaMillisecondsInt
from conflict_interface.data_types.custom_types import UnmodifiableCollection, HashMap, HashSet, LinkedHashMap
from conflict_interface.data_types.custom_types import UnmodifiableMap
from conflict_interface.data_types.custom_types import UnmodifiableSet
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.mod_state.boost import Boost
from conflict_interface.data_types.player_state.faction import Faction


@dataclass
class SortingConfig(GameObject):
    C = "ultshared.modding.configuration.UltSortingConfig"
    sorting_order: int
    MAPPING = {"sorting_order": "sortOrder"}


@dataclass
class SoundConfig(GameObject):
    C = "ultshared.modding.configuration.UltSoundConfig"

    action_sounds: Optional[RegularImmutableMap[str, str]]

    MAPPING = {
        "action_sounds": "actionSounds",
    }

@dataclass
class FreeFormSoundConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"

    MAPPING = {
    }


@dataclass
class AirplaneConfig(GameObject):
    C = "ultshared.modding.configuration.UltAirplaneConfig"
    spy: bool
    patrol_radius: int
    patrol_target_damage_types: UnmodifiableCollection[int]
    embarkation_time: int
    disembarkation_time: int
    refuel_time: int
    max_flight_time: Optional[int] # Timedelta seconds


    MAPPING = {
        "spy": "spy",
        "patrol_radius": "patrolRadius",
        "patrol_target_damage_types": "patrolTargetDamageTypes",
        "embarkation_time": "embarkationTime",
        "disembarkation_time": "disembarkationTime",
        "refuel_time": "refuelTime",
        "max_flight_time": "maxFlightTime",

    }


@dataclass
class ControllableConfig(GameObject):
    C = "ultshared.modding.configuration.UltControllableConfig"
    controllable: bool
    MAPPING = {"controllable": "controllable"}


def parse_dict_of_ints(obj):
    obj.pop("@")
    return {int(key): val for key, val in obj.items()}


@dataclass
class CarrierConfig(GameObject):
    C = "ultshared.modding.configuration.UltCarrierConfig"
    slot_config: HashMap[int, int]
    max_capacity: int

    MAPPING = {
            "slot_config": "slotConfig",
            "max_capacity": "maxCapacity"
    }


@dataclass
class AntiAirConfig(GameObject):
    C = "ultshared.modding.configuration.UltAntiAirConfig"
    range: int
    attackPainter: Optional[str]
    MAPPING = {"range": "range",
               "attackPainter": "attackPainter"}


@dataclass
class DummyScoutConfig(GameObject):
    C = "ultshared.modding.configuration.UltScoutConfig$DummyScoutConfig"
    stealth_classes: Union[EmptyList[int], UnmodifiableCollection[int]]
    camoflage_classes: Union[EmptyList[int], UnmodifiableCollection[int]]

    MAPPING = {
            "stealth_classes": "stealthClasses",
            "camoflage_classes": "camouflageClasses",
    }

@dataclass
class ScoutConfig(GameObject):
    C = "ultshared.modding.configuration.UltScoutConfig"
    stealth_classes: Union[EmptyList[int], UnmodifiableCollection[int]]
    camoflage_classes: Union[EmptyList[int], UnmodifiableCollection[int]]

    MAPPING = {
            "stealth_classes": "stealthClasses",
            "camoflage_classes": "camouflageClasses",
    }


@dataclass
class TokenProducerConfigProduction(GameObject):
    C = "ultshared.modding.configuration.UltTokenProducerConfig$TokenProduction"
    type_id: int
    amount: int
    duration: TimeDeltaMillisecondsInt = TimeDeltaMillisecondsInt(0)
    MAPPING = {
            "type_id": "typeID",
            "amount": "amount",
            "duration": "duration",
    }

@dataclass
class TokenProducerConfig(GameObject):
    C = "ultshared.modding.configuration.UltTokenProducerConfig"
    tokens_on_spawn: UnmodifiableCollection[TokenProducerConfigProduction]
    tokens_provided: UnmodifiableCollection[TokenProducerConfigProduction]

    MAPPING = {
            "tokens_on_spawn": "tokensOnSpawn",
            "tokens_provided": "tokensProvided",
    }

@dataclass
class TokenRequirement(GameObject): # TODO consider move to own file
    C = "ultshared.modding.configuration.UltTokenConsumerConfig$TokenRequirement"
    type_id: int
    amount: int

    MAPPING = {
        "type_id": "typeID",
        "amount": "amount",
    }


@dataclass
class TokenConsumerConfig(GameObject):
    C = "ultshared.modding.configuration.UltTokenConsumerConfig"

    requirements: UnmodifiableCollection[TokenRequirement]

    MAPPING = {
            "requirements": "requirements",
    }


@dataclass
class DummyMissileConfig(GameObject):
    C = "ultshared.modding.configuration.UltMissileConfig$DummyMissileConfig"
    missile_slot: int
    stacking_limit: int
    launch_behaviour: str = ""

    MAPPING = {
        "launch_behaviour": "launchBehavior",
        "missile_slot": "missileSlot",
        "stacking_limit": "stackingLimit",
    }

@dataclass
class MissileConfig(GameObject):
    C = "ultshared.modding.configuration.UltMissileConfig"
    missile_slot: int
    stacking_limit: int
    launch_behaviour: str = ""

    MAPPING = {
        "launch_behaviour": "launchBehavior",
        "missile_slot": "missileSlot",
        "stacking_limit": "stackingLimit",
    }

@dataclass
class MissileSlotConfig(GameObject):
    C = "ultshared.modding.configuration.MissileSlotConfig"

    capacity: int
    resupply_time: int
    initial_inventory: int

    MAPPING = {
        "capacity": "capacity",
        "resupply_time": "resupplyTime",
        "initial_inventory": "initialInventory",
    }


@dataclass
class MissileCarrierConfig(GameObject):
    C = "ultshared.modding.configuration.UltMissileCarrierConfig"
    missile_slot_config: Union[HashMap[int, MissileSlotConfig], LinkedHashMap[int, MissileSlotConfig], EmptyMap[int, MissileSlotConfig]]

    MAPPING = {
        "missile_slot_config": "missileSlotConfig",
    }

@dataclass
class DummyMissileCarrierConfig(GameObject):
    C = "ultshared.modding.configuration.UltMissileCarrierConfig$DummyMissileCarrierConfig"
    missile_slot_config: EmptyMap[int, MissileSlotConfig]

    MAPPING = {
        "missile_slot_config": "missileSlotConfig",
    }

@dataclass
class MissileCarrierFeature(GameObject):
    C ="ultshared.warfare.UltMissileCarrierFeature"
    missile_carrier_config: MissileCarrierConfig
    inventory: HashMap[int, int]
    last_missile_pawns: HashMap[int, DateTimeMillisecondsInt] # TODO Type checking

    MAPPING = {
        "missile_carrier_config": "missileCarrierConfig",
        "inventory": "inventory",
        "last_missile_pawns": "lastMissileSpawns",
    }


@dataclass
class RadarSignatureFeature(GameObject):
    C = "ultshared.warfare.UltRadarSignatureFeature"
    signature_size_map: HashMap[int, int]
    MAPPING = {
        "signature_size_map": "ssm",
    }


@dataclass
class TokenFeature(GameObject):
    """
    Not implemented. There exists no knowledge
    about how they work.
    """
    C = "ultshared.tokens.UltTokenFeature"
    tokens: HashSet[int] # TODO no idea if its int int (no examples in data1)
    MAPPING = {
        "tokens": "tokens",
    }


@dataclass
class CarrierFeature(GameObject):
    """
    Not implemented. There exists no knowledge
    about how they work.
    """
    MAPPING = {}

@dataclass
class MoraleBasedProductionConfig(GameObject):
    C = "ultshared.modding.configuration.UltMoraleBasedProductionConfig" # Stupid naming
    curve_x1: float
    curve_x2: float
    curve_y1: float
    curve_y2: float

    MAPPING = {
        "curve_x1": "curveX1",
        "curve_x2": "curveX2",
        "curve_y1": "curveY1",
        "curve_y2": "curveY2",
    }

@dataclass
class HealArmiesModFeatureConfig(GameObject):
    C = "ultshared.modding.configuration.UltHealArmiesModFeatureConfig"
    healing_rate_by_terrain_type: LinkedHashMap[int, float]
    tick_time: int
    MAPPING = {
        "healing_rate_by_terrain_type": "healingRateByTerrainType",
        "tick_time": "tickTime",
    }

@dataclass
class HealArmiesUpgradeFeatureConfig(GameObject):
    C = "ultshared.modding.configuration.UltHealArmiesUpgradeFeatureConfig"
    healing_rate_by_armor_class: LinkedHashMap[int, float]
    MAPPING = {
        "healing_rate_by_armor_class": "healingRateByArmorClass",
    }

@dataclass
class ReducedDamageArmorClassesConfig(GameObject):
    C = "ultshared.modding.configuration.ReducedDamageArmorClassesConfig"

    reduced_to_whole: LinkedHashMap[int, int]

    MAPPING = {
        "reduced_to_whole": "reducedToWhole",
    }

@dataclass
class ArmyStackingPenaltyConfig(GameObject):
    C = "ultshared.modding.configuration.UltArmyStackingPenaltyConfig"

    damage_factor_scaling: LinkedHashMap[int, ConstantSegmentFunction]
    speed_factor_scaling: LinkedHashMap[int, ConstantSegmentFunction]

    MAPPING = {
        "damage_factor_scaling": "damageFactorScalings",
        "speed_factor_scaling": "speedFactorScalings",
    }

@dataclass
class AStarConfig(GameObject):
    C = "ultshared.modding.configuration.UltAStarConfig"

    war_declearation_cost: int
    enemy_harbour_cost_factor: float
    friendly_harbour_cost_factor: float

    MAPPING = {
        "war_declearation_cost": "warDeclarationCost",
        "enemy_harbour_cost_factor": "enemyHarbourCostFactor",
        "friendly_harbour_cost_factor": "friendlyHarbourCostFactor",
    }

@dataclass
class NoobBonusConfig(GameObject):
    C = "ultshared.modding.configuration.UltNoobBonusConfig"

    days: int
    recruit_time_reduction: float
    resource_production_bonus: float

    MAPPING = {
        "days": "days",
        "recruit_time_reduction": "recruitTimeReduction",
        "resource_production_bonus": "resourceProductionBonus",
    }

@dataclass
class ModStateFrontendConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"

    map_custom_asset_override_config: dict[str, dict[int, int]]
    radar_config: dict[str, dict[int, int]]
    flag_config: dict[str, bool]
    game_info_config: dict[int, str] # TODO strings are links
    consts: dict[str, int]
    community_you_tube: dict[str, Union[str, int]]
    factor_bonus_tooltip: dict[str, list[int]]
    ticket_item_ids: list[int]


    MAPPING = {
        "map_custom_asset_override_config": "mapCustomAssetOverrideConfig",
        "radar_config": "RadarConfig",
        "flag_config": "flagConfig",
        "game_info_config": "gameInfoConfig",
        "consts": "consts",
        "community_you_tube": "communityYouTube",
        "factor_bonus_tooltip": "factorBonusTooltip",
        "ticket_item_ids": "ticketItemIDs",
    }

@dataclass
class UnitTypeFrontEndConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"
    player_progression_image: Optional[str]

    MAPPING = {
        "player_progression_image": "playerProgressionImage",
    }

@dataclass
class FreeformConfig(GameObject):
    C = ""



@dataclass
class UpgradeTypeFreeformConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"

    visibility: Optional[dict[str, bool]]
    construction_visibility: Optional[dict[str, bool]]
    highlight: Optional[dict[str, bool]]
    sound_id: Optional[str]

    MAPPING = {
        "visibility": "visibility",
        "construction_visibility": "constructionVisibility",
        "highlight": "highlight",
        "sound_id": "soundID"
    }


@dataclass
class ConstructionSpeedupConfig(GameObject):
    C = "ultshared.modding.configuration.UltConstructionSpeedupConfig"

    factor: float
    construction_class: int

    MAPPING = {
        "factor": "factor",
        "construction_class": "constructionClass",
    }

@dataclass
class DiplomaticAggressionConfig(GameObject):
    C = "ultshared.modding.configuration.UltDiplomaticAggressionConfig"

    incident_mapping: UnmodifiableMap[str, int] # TODO key could be enum
    victim_incident_mapping: UnmodifiableMap[int, int] # TODO check typing

    MAPPING = {
        "incident_mapping": "incidentMapping",
        "victim_incident_mapping": "victimIncidentMapping",
    }

@dataclass
class AirMobileConfig(GameObject):
    C = "ultshared.modding.configuration.UltAirMobileConfig"

    assault_type: str # TODO could be enum

    MAPPING = {
        "assault_type": "assaultType", # TODO why is an ide warning here?
    }

@dataclass
class ArmyBoostConfig(GameObject):
    C = "ultshared.modding.configuration.UltArmyBoostConfig"

    bonuses: HashSet[Boost]

    MAPPING = {
        "bonuses": "bonuses",
    }

@dataclass
class LimitedMobilizationConfig(GameObject):
    C = "ultshared.modding.configuration.UltLimitedMobilizationConfig"

    limit: int
    MAPPING = {
        "limit": "limit",
    }

@dataclass
class RadarSignatureConfig(GameObject):
    C = "ultshared.modding.configuration.UltRadarSignatureConfig"

    type: int
    size: int

    MAPPING = {
        "type": "type",
        "size": "size",
    }


@dataclass
class SignatureConfig(GameObject):
    C = "ultshared.modding.configuration.UltRadarConfig$SignatureConfig"

    range: int
    resolution: int

    MAPPING = {
        "range": "range",
        "resolution": "resolution",
    }

@dataclass
class RadarConfig(GameObject):
    C = "ultshared.modding.configuration.UltRadarConfig"

    signature_types: LinkedHashMap[int, SignatureConfig]

    MAPPING = {
        "signature_types": "signatureTypes",
    }

@dataclass
class ConvertToResourceConfig(GameObject):
    C = "ultshared.modding.configuration.UltConvertToResourceConfig"

    resources: HashMap[int, int]

    MAPPING = {
        "resources": "resources",
    }

@dataclass
class DisbandConfig(GameObject):
    C = "ultshared.modding.configuration.UltDisbandConfig"

    resources_returned: float
    duration: int

    MAPPING = {
        "resources_returned": "resourcesReturned",
        "duration": "duration",
    }

@dataclass
class MissionTypeFrontEndConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"
    icon: str
    help: dict[str, str]

    MAPPING = {
        "icon": "icon",
        "help": "help",
    }

@dataclass
class DurationStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltDurationStrategyConfig"
    duration: int
    strategy: str # TODO could be enum

    MAPPING = {
        "duration": "duration",
        "strategy": "strategy",
    }

@dataclass
class TokenClassConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltTokenClassConfig"
    token_class: int

    MAPPING = {
        "token_class": "tokenClass",
    }

@dataclass
class TokenPriorityConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltTokenPriorityConfig"
    priority: int

    MAPPING = {
        "priority": "priority",
    }

@dataclass
class SplitStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltSplitStrategyConfig"
    strategy: str # TODO could be enum

    MAPPING = {
        "strategy": "strategy",
    }

@dataclass
class EffectsConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltEffectsConfig"
    effects: ArrayList[dict[str, Union[float, str, int]]] # TODO check typing

    MAPPING = {
        "effects": "effects",
    }

@dataclass
class ConflictCondition(GameObject):
    C = "ultshared.modding.configuration.UltCondition"
    expression: str

    MAPPING = {
        "expression": "expression",
    }


@dataclass
class PurchaseStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltPurchaseStrategyConfig"

    purchasable: bool
    requirements: ConflictCondition
    costs: Union[LinkedHashMap[int, int], HashMap[int, int]]
    enable_all_priority: bool = False
    initial_count: int = 0
    MAPPING = {
        "purchasable": "purchasable",
        "requirements": "requirements",
        "costs": "costs",
        "initial_count": "initialCount",
        "enable_all_priority": "enableAllPriority",
    }

@dataclass
class MergeStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltMergeStrategyConfig"
    strategy: str

    MAPPING = {
        "strategy": "strategy",
    }

@dataclass
class VisibilityStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltVisibilityStrategyConfig"
    minimum_relation: int

    MAPPING = {
        "minimum_relation": "minimumRelation",
    }

@dataclass
class EffectScalingStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltEffectScalingStrategyConfig"
    strategy: str

    MAPPING = {
        "strategy": "strategy",
    }

@dataclass
class Consumption(GameObject):
    C = "ultshared.modding.configuration.tokens.UltConsumption"
    consumption: ArrayList[int] # TODO check typing

    MAPPING = {
        "consumption": "consumption",
    }

@dataclass
class RenderConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"
    faction_specific_images: Optional[bool]
    icon: Optional[str]
    background_image: Optional[str]

    MAPPING = {
        "faction_specific_images": "factionSpecificImages",
        "icon": "icon",
        "background_image": "backgroundImage",
    }

@dataclass
class SpyConfig(GameObject):
    C = "ultshared.modding.configuration.UltSpyConfig"
    max_foreign_spies_per_province: int

    MAPPING = {
        "max_foreign_spies_per_province": "maxForeignSpiesPerProvince",
    }

@dataclass
class NewspaperConfig(GameObject):
    C = "ultshared.modding.configuration.UltNewspaperConfig"

    max_articles: int
    max_article_title_characters: int
    max_article_body_characters: int

    MAPPING = {
        "max_articles": "maxArticles",
        "max_article_title_characters": "maxArticleTitleChars",
        "max_article_body_characters": "maxArticleBodyChars",
    }

@dataclass
class UberConfig(GameObject):
    # freeform config
    C = "ultshared.modding.configuration.UltFreeformConfig"

    MAPPING = {}

@dataclass
class IncludeExcludeConfig(GameObject):
    C = "ultshared.modding.configuration.UltIncludeExcludeConfig"

    include: UnmodifiableSet[int]
    exclude: UnmodifiableSet[int]

    MAPPING = {
        "include": "include",
        "exclude": "exclude",
    }

@dataclass
class PlayerProgressionConfig(GameObject):
    C = "ultshared.modding.configuration.UltPlayerProgressionConfig"

    scenarios: IncludeExcludeConfig
    unit_types: IncludeExcludeConfig

    MAPPING = {
        "scenarios": "scenarios",
        "unit_types": "unitTypes",
    }

@dataclass
class ConsumptionStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltConsumptionStrategyConfig"

    consumption_events: Optional[ArrayList[int]] # TODO check typing
    behavior: Optional[str]
    insufficient_rule: Optional[str]

    MAPPING = {
        "consumption_events": "consumptionEvents",
        "behavior": "behavior",
        "insufficient_rule": "insufficientRule",
    }

@dataclass
class FactorySpeedUpConfig(GameObject):
    C = "ultshared.modding.configuration.UltFactorySpeedUpConfig"

    byUnitType: UnmodifiableCollection[int] # TODO check typing
    base: float

    MAPPING = {
        "byUnitType": "byUnitType",
        "base": "base",
    }

@dataclass
class VictoryPointsGenerationConfig(GameObject):
    C = "ultshared.modding.configuration.UltVictoryPointsGenerationConfig"

    daily_victory_points: int

    MAPPING = {
        "daily_victory_points": "dailyVictoryPoints",
    }

@dataclass
class StackingConfig(GameObject):
    C = "ultshared.modding.configuration.UltStackingConfig"

    stacking_limit: int
    cls: int

    MAPPING = {
        "stacking_limit": "limit",
        "cls": "class",
    }

@dataclass
class LaunchTargetConfig(GameObject):
    C = "ultshared.modding.configuration.UltLaunchTargetConfig"

    follow_target: bool
    possible_targets: HashSet[str] # TODO could be enum

    MAPPING = {
        "follow_target": "followTarget",
        "possible_targets": "possibleTargets",
    }

@dataclass
class TokenSensitivityConfig(GameObject):
    C = "ultshared.modding.configuration.UltTokenSensitivityConfig"

    token_types: UnmodifiableCollection[int]

    MAPPING = {
        "token_types": "tokenTypes",
    }

@dataclass
class FactionSpecificConfig(GameObject):
    C = "ultshared.modding.configuration.UltFactionSpecificConfig"

    factions: HashSet[Faction]

    MAPPING = {
        "factions": "factions",
    }

