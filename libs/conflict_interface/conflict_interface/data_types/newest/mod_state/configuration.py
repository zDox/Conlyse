from dataclasses import dataclass
from enum import StrEnum
from typing import Optional
from typing import Union

from ..constant_segment_function import ConstantSegmentFunction
from ..custom_types import ArrayList
from ..custom_types import DateTimeMillisecondsInt
from ..custom_types import EmptyList
from ..custom_types import EmptyMap
from ..custom_types import HashMap
from ..custom_types import HashSet
from ..custom_types import LinkedHashMap
from ..custom_types import RegularImmutableMap
from ..custom_types import TimeDeltaMillisecondsInt
from ..custom_types import UnmodifiableCollection
from ..custom_types import UnmodifiableMap
from ..custom_types import UnmodifiableSet
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..mod_state.boost import Boost
from ..player_state.faction import Faction

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class SortingConfig(GameObject):
    C = "ultshared.modding.configuration.UltSortingConfig"
    sorting_order: int
    MAPPING = {"sorting_order": "sortOrder"}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class SoundConfig(GameObject):
    C = "ultshared.modding.configuration.UltSoundConfig"

    action_sounds: Optional[RegularImmutableMap[str, str]]

    MAPPING = {
        "action_sounds": "actionSounds",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class FreeFormSoundConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"

    MAPPING = {
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class ControllableConfig(GameObject):
    C = "ultshared.modding.configuration.UltControllableConfig"
    controllable: bool
    MAPPING = {"controllable": "controllable"}


def parse_dict_of_ints(obj):
    obj.pop("@")
    return {int(key): val for key, val in obj.items()}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class CarrierConfig(GameObject):
    C = "ultshared.modding.configuration.UltCarrierConfig"
    slot_config: HashMap[int, int]
    max_capacity: int

    MAPPING = {
            "slot_config": "slotConfig",
            "max_capacity": "maxCapacity"
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class AntiAirConfig(GameObject):
    C = "ultshared.modding.configuration.UltAntiAirConfig"
    range: int
    attackPainter: Optional[str]
    MAPPING = {"range": "range",
               "attackPainter": "attackPainter"}

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class DummyScoutConfig(GameObject):
    C = "ultshared.modding.configuration.UltScoutConfig$DummyScoutConfig"
    stealth_classes: Union[EmptyList[int], UnmodifiableCollection[int]]
    camoflage_classes: Union[EmptyList[int], UnmodifiableCollection[int]]

    MAPPING = {
            "stealth_classes": "stealthClasses",
            "camoflage_classes": "camouflageClasses",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class ScoutConfig(GameObject):
    C = "ultshared.modding.configuration.UltScoutConfig"
    stealth_classes: Union[EmptyList[int], UnmodifiableCollection[int]]
    camoflage_classes: Union[EmptyList[int], UnmodifiableCollection[int]]

    MAPPING = {
            "stealth_classes": "stealthClasses",
            "camoflage_classes": "camouflageClasses",
    }

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class TokenProducerConfigProduction(GameObject):
    C = "ultshared.modding.configuration.UltTokenProducerConfig$TokenProduction"
    type_id: int
    amount: int
    range: int
    duration: TimeDeltaMillisecondsInt = TimeDeltaMillisecondsInt(0)
    MAPPING = {
        "type_id": "typeID",
        "amount": "amount",
        "duration": "duration",
        "range": "range",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TokenProducerConfig(GameObject):
    C = "ultshared.modding.configuration.UltTokenProducerConfig"
    tokens_on_spawn: UnmodifiableCollection[TokenProducerConfigProduction]
    tokens_provided: UnmodifiableCollection[TokenProducerConfigProduction]

    MAPPING = {
            "tokens_on_spawn": "tokensOnSpawn",
            "tokens_provided": "tokensProvided",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TokenRequirement(GameObject): # TODO consider move to own file
    C = "ultshared.modding.configuration.UltTokenConsumerConfig$TokenRequirement"
    type_id: int
    amount: int

    MAPPING = {
        "type_id": "typeID",
        "amount": "amount",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TokenConsumerConfig(GameObject):
    C = "ultshared.modding.configuration.UltTokenConsumerConfig"

    requirements: UnmodifiableCollection[TokenRequirement]

    MAPPING = {
            "requirements": "requirements",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class MissileCarrierConfig(GameObject):
    C = "ultshared.modding.configuration.UltMissileCarrierConfig"
    missile_slot_config: Union[HashMap[int, MissileSlotConfig], LinkedHashMap[int, MissileSlotConfig], EmptyMap[int, MissileSlotConfig]]

    MAPPING = {
        "missile_slot_config": "missileSlotConfig",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class DummyMissileCarrierConfig(GameObject):
    C = "ultshared.modding.configuration.UltMissileCarrierConfig$DummyMissileCarrierConfig"
    missile_slot_config: EmptyMap[int, MissileSlotConfig]

    MAPPING = {
        "missile_slot_config": "missileSlotConfig",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class RadarSignatureFeature(GameObject):
    C = "ultshared.warfare.UltRadarSignatureFeature"
    signature_size_map: HashMap[int, int]
    MAPPING = {
        "signature_size_map": "ssm",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class CarrierFeature(GameObject):
    """
    Not implemented. There exists no knowledge
    about how they work.
    """
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class HealArmiesModFeatureConfig(GameObject):
    C = "ultshared.modding.configuration.UltHealArmiesModFeatureConfig"
    healing_rate_by_terrain_type: LinkedHashMap[int, float]
    tick_time: int
    MAPPING = {
        "healing_rate_by_terrain_type": "healingRateByTerrainType",
        "tick_time": "tickTime",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class HealArmiesUpgradeFeatureConfig(GameObject):
    C = "ultshared.modding.configuration.UltHealArmiesUpgradeFeatureConfig"
    healing_rate_by_armor_class: LinkedHashMap[int, float]
    MAPPING = {
        "healing_rate_by_armor_class": "healingRateByArmorClass",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ReducedDamageArmorClassesConfig(GameObject):
    C = "ultshared.modding.configuration.ReducedDamageArmorClassesConfig"

    reduced_to_whole: LinkedHashMap[int, int]

    MAPPING = {
        "reduced_to_whole": "reducedToWhole",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ArmyStackingPenaltyConfig(GameObject):
    C = "ultshared.modding.configuration.UltArmyStackingPenaltyConfig"

    damage_factor_scaling: LinkedHashMap[int, ConstantSegmentFunction]
    speed_factor_scaling: LinkedHashMap[int, ConstantSegmentFunction]

    MAPPING = {
        "damage_factor_scaling": "damageFactorScalings",
        "speed_factor_scaling": "speedFactorScalings",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ModStateFrontendConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"

    map_custom_asset_override_config: dict[str, dict[int, int]]
    radar_config: dict[str, dict[int, int]]
    flag_config: dict[str, bool]
    game_info_config: dict[int, str] # TODO strings are links
    consts: dict[str, int]
    community_you_tube: dict[str, Union[int, str]]
    factor_bonus_tooltip: dict[str, list[int]]
    ticket_item_ids: list[int]
    show_veteran_separation_text: bool
    solsten_survey_details: dict[str, Union[int ,str]]
    officer_promo_banner: dict[str, Union[bool, int, str]]
    feature_promo_popup: dict[str, Union[bool, int, str]]




    MAPPING = {
        "map_custom_asset_override_config": "mapCustomAssetOverrideConfig",
        "radar_config": "RadarConfig",
        "flag_config": "flagConfig",
        "game_info_config": "gameInfoConfig",
        "consts": "consts",
        "community_you_tube": "communityYouTube",
        "factor_bonus_tooltip": "factorBonusTooltip",
        "ticket_item_ids": "ticketItemIDs",
        "show_veteran_separation_text": "showVeteranSeparationText",
        "solsten_survey_details": "solstenSurveyDetails",
        "officer_promo_banner": "officerPromoBanner",
        "feature_promo_popup": "featurePromoPopup",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UnitTypeFrontEndConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"
    player_progression_image: Optional[str]
    officer_premium_id: Optional[int]

    MAPPING = {
        "player_progression_image": "playerProgressionImage",
        "officer_premium_id": "officerPremiumItemID",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class FreeformConfig(GameObject):
    C = ""
    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UpgradeTypeFreeformConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"

    visibility: Optional[dict[str, bool]]
    construction_visibility: Optional[dict[str, bool]]
    highlight: Optional[dict[str, bool]]
    sound_id: Optional[str]
    animation_id: Optional[str]

    MAPPING = {
        "visibility": "visibility",
        "construction_visibility": "constructionVisibility",
        "highlight": "highlight",
        "sound_id": "soundID",
        "animation_id": "animationId",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PremiumVisibilityConfig(GameObject):
    C = "ultshared.modding.configuration.premiums.UltPremiumVisibilityConfig"
    visibility: str
    MAPPING = {
        "visibility": "visibility",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ConstructionSpeedupConfig(GameObject):
    C = "ultshared.modding.configuration.UltConstructionSpeedupConfig"

    factor: float
    construction_class: int

    MAPPING = {
        "factor": "factor",
        "construction_class": "constructionClass",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class DiplomaticAggressionConfig(GameObject):
    C = "ultshared.modding.configuration.UltDiplomaticAggressionConfig"

    incident_mapping: UnmodifiableMap[str, int] # TODO key could be enum
    victim_incident_mapping: UnmodifiableMap[int, int] # TODO check typing

    MAPPING = {
        "incident_mapping": "incidentMapping",
        "victim_incident_mapping": "victimIncidentMapping",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class AirMobileConfig(GameObject):
    C = "ultshared.modding.configuration.UltAirMobileConfig"

    assault_type: str # TODO could be enum

    MAPPING = {
        "assault_type": "assaultType", # TODO why is an ide warning here?
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ArmyBoostConfig(GameObject):
    C = "ultshared.modding.configuration.UltArmyBoostConfig"

    bonuses: HashSet[Boost]

    MAPPING = {
        "bonuses": "bonuses",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class LimitedMobilizationConfig(GameObject):
    C = "ultshared.modding.configuration.UltLimitedMobilizationConfig"

    limit: int
    MAPPING = {
        "limit": "limit",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class RadarSignatureConfig(GameObject):
    C = "ultshared.modding.configuration.UltRadarSignatureConfig"

    type: int
    size: int

    MAPPING = {
        "type": "type",
        "size": "size",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class SignatureConfig(GameObject):
    C = "ultshared.modding.configuration.UltRadarConfig$SignatureConfig"

    range: int
    resolution: int

    MAPPING = {
        "range": "range",
        "resolution": "resolution",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class RadarConfig(GameObject):
    C = "ultshared.modding.configuration.UltRadarConfig"

    signature_types: LinkedHashMap[int, SignatureConfig]

    MAPPING = {
        "signature_types": "signatureTypes",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ConvertToResourceConfig(GameObject):
    C = "ultshared.modding.configuration.UltConvertToResourceConfig"

    resources: HashMap[int, int]

    MAPPING = {
        "resources": "resources",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class DisbandConfig(GameObject):
    C = "ultshared.modding.configuration.UltDisbandConfig"

    resources_returned: float
    duration: int

    MAPPING = {
        "resources_returned": "resourcesReturned",
        "duration": "duration",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class MissionTypeFrontEndConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"
    icon: str
    help: dict[str, str]

    MAPPING = {
        "icon": "icon",
        "help": "help",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class DurationStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltDurationStrategyConfig"
    duration: int
    strategy: str # TODO could be enum

    MAPPING = {
        "duration": "duration",
        "strategy": "strategy",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TokenClassConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltTokenClassConfig"
    token_class: int

    MAPPING = {
        "token_class": "tokenClass",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TokenPriorityConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltTokenPriorityConfig"
    priority: int

    MAPPING = {
        "priority": "priority",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class SplitStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltSplitStrategyConfig"
    strategy: str # TODO could be enum

    MAPPING = {
        "strategy": "strategy",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class EffectsConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltEffectsConfig"
    effects: ArrayList[dict[str, Union[float, str, int, UnmodifiableSet[int], TokenProducerConfig]]] # TODO check typing

    MAPPING = {
        "effects": "effects",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ConflictCondition(GameObject):
    C = "ultshared.modding.configuration.UltCondition"
    expression: str

    MAPPING = {
        "expression": "expression",
    }

@conflict_serializable(SerializationCategory.ENUM, version=VERSION)
class PossiblePosition(StrEnum):
    ProvinceCenter = "PROVINCE_CENTRE"
    SeaConnections = "SEA_CONNECTIONS"
    LandConnections = "LAND_CONNECTIONS"

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PositionConfig(GameObject):
    C = "ultshared.modding.configuration.UltPositionConfig"
    possible_positions: HashSet[PossiblePosition]

    MAPPING = {
        "possible_positions": "possiblePositions",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class MergeStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltMergeStrategyConfig"
    strategy: str

    MAPPING = {
        "strategy": "strategy",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class VisibilityStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltVisibilityStrategyConfig"
    minimum_relation: int

    MAPPING = {
        "minimum_relation": "minimumRelation",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class EffectScalingStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltEffectScalingStrategyConfig"
    strategy: str

    MAPPING = {
        "strategy": "strategy",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class Consumption(GameObject):
    C = "ultshared.modding.configuration.tokens.UltConsumption"
    consumption: ArrayList[int] # TODO check typing

    MAPPING = {
        "consumption": "consumption",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class RenderConfig(GameObject):
    C = "ultshared.modding.configuration.UltFreeformConfig"
    faction_specific_images: Optional[bool]
    icon: Optional[str]
    background_image: Optional[str]
    effective_charge: Optional[str]
    directional: bool = False

    MAPPING = {
        "faction_specific_images": "factionSpecificImages",
        "icon": "icon",
        "background_image": "backgroundImage",
        "directional": "directional",
        "effective_charge": "effectiveCharge",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class SpyConfig(GameObject):
    C = "ultshared.modding.configuration.UltSpyConfig"
    max_foreign_spies_per_province: int

    MAPPING = {
        "max_foreign_spies_per_province": "maxForeignSpiesPerProvince",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
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

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UberConfig(GameObject):
    # freeform config
    C = "ultshared.modding.configuration.UltFreeformConfig"

    MAPPING = {}

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class IncludeExcludeConfig(GameObject):
    C = "ultshared.modding.configuration.UltIncludeExcludeConfig"

    include: UnmodifiableSet[Union[int, str, bool, float]]
    exclude: UnmodifiableSet[Union[int, str, bool, float]]

    MAPPING = {
        "include": "include",
        "exclude": "exclude",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class PlayerProgressionConfig(GameObject):
    C = "ultshared.modding.configuration.UltPlayerProgressionConfig"

    scenarios: IncludeExcludeConfig
    unit_types: IncludeExcludeConfig

    MAPPING = {
        "scenarios": "scenarios",
        "unit_types": "unitTypes",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class ConsumptionStrategyConfig(GameObject):
    C = "ultshared.modding.configuration.tokens.UltConsumptionStrategyConfig"

    consumption_events: Optional[ArrayList[str]] # TODO check typing
    behavior: Optional[str]
    insufficient_rule: Optional[str]

    MAPPING = {
        "consumption_events": "consumptionEvents",
        "behavior": "behavior",
        "insufficient_rule": "insufficientRule",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class FactorySpeedUpConfig(GameObject):
    C = "ultshared.modding.configuration.UltFactorySpeedUpConfig"

    byUnitType: UnmodifiableCollection[int] # TODO check typing
    base: float

    MAPPING = {
        "byUnitType": "byUnitType",
        "base": "base",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class VictoryPointsGenerationConfig(GameObject):
    C = "ultshared.modding.configuration.UltVictoryPointsGenerationConfig"

    daily_victory_points: int

    MAPPING = {
        "daily_victory_points": "dailyVictoryPoints",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class StackingConfig(GameObject):
    C = "ultshared.modding.configuration.UltStackingConfig"

    stacking_limit: int
    cls: int

    MAPPING = {
        "stacking_limit": "limit",
        "cls": "class",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UnitSpawnDetails(GameObject):
    C = "ultshared.modding.configuration.UltUnitSpawnConfig$UnitSpawnDetails"
    chance: float
    spawn_condition: ConflictCondition
    
    MAPPING = {
        "chance": "chance",
        "spawn_condition": "spawnCondition",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class UnitSpawnConfig(GameObject):
    C = "ultshared.modding.configuration.UltUnitSpawnConfig"
    units: LinkedHashMap[str, UnitSpawnDetails]
    rounds_per_day: int
    spawn_during_combat: bool
    spawn_condition: ConflictCondition

    MAPPING = {
        "units": "units",
        "rounds_per_day": "roundsPerDay",
        "spawn_during_combat": "spawnDuringCombat",
        "spawn_condition": "spawnCondition",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class LaunchTargetConfig(GameObject):
    C = "ultshared.modding.configuration.UltLaunchTargetConfig"

    follow_target: bool
    possible_targets: HashSet[str] # TODO could be enum

    MAPPING = {
        "follow_target": "followTarget",
        "possible_targets": "possibleTargets",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TokenSensitivityConfig(GameObject):
    C = "ultshared.modding.configuration.UltTokenSensitivityConfig"

    token_types: UnmodifiableCollection[int]

    MAPPING = {
        "token_types": "tokenTypes",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class FactionSpecificConfig(GameObject):
    C = "ultshared.modding.configuration.UltFactionSpecificConfig"

    factions: HashSet[Faction]

    MAPPING = {
        "factions": "factions",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class VariantConfig(GameObject):
    C = "ultshared.modding.configuration.UltVariantConfig"

    variant_class: int

    MAPPING = {
        "variant_class": "class",
    }

@conflict_serializable(SerializationCategory.DATACLASS, version=VERSION)
@dataclass
class TerrainRestrictedConfig(GameObject):
    C = "ultshared.modding.configuration.UltTerrainRestrictionConfig"

    restricted_terrains: HashSet[int] # TODO though it is terrain type but value can be 22 which is not terrain
    MAPPING = {
        "restricted_terrains": "restrictedTerrains",
    }

