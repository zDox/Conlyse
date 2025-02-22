
from conflict_interface.utils import GameObject, ConMapping

from dataclasses import dataclass
from datetime import timedelta

from conflict_interface.data_types.modding.configuration import \
        MissileConfig, SortingConfig, SoundConfig, AirplaneConfig, \
        ControllableConfig, CarrierConfig, AntiAirConfig, ScoutConfig, \
        TokenProducerConfig, TokenConsumerConfig

from .unit_feature import UnitFeature
from ...utils.json_mapped_class import JavaTypes, HashMap
from typing import List

class RenderConfig:
    pass


@dataclass
class UnitType(GameObject):
    id: int
    stats_column_id: int
    unit_pack: int
    ranking_factor: int
    build_time: timedelta
    costs: HashMap[int, float]
    daily_costs: HashMap[int, float]
    speeds: HashMap[int, float]
    hit_points: HashMap[int, float]
    damage_types: HashMap[int, float]
    damage_area: HashMap[int, float]
    strength: HashMap[int, float]
    defense: HashMap[int, float]
    ranges: HashMap[int, float]
    view_widths: HashMap[int, float]
    required_upgrades: HashMap[int, int]
    required_researches: HashMap[int, int]
    unit_cap_research_items: HashMap[int, int]
    friendly_speed_factor: float
    foreign_speed_factor: float
    identifier: str
    minimum_tech_level: int
    unit_features: HashMap[UnitFeature, float]
    size_factors: HashMap[int, float]
    attack_painter: str
    pin_painter: str
    unit_class: int
    set: int
    formation_name_small: str
    formation_name_big: str
    unit_description: str
    name_faction1: str
    name_faction2: str
    name_faction3: str
    name_faction4: str
    type_name: str
    sorting_config: SortingConfig
    sound_config: SoundConfig
    airplane_config: AirplaneConfig
    controllable_config: ControllableConfig
    carrier_config: CarrierConfig
    type_size_name: str
    sort_value: int
    producible: bool
    missile_config: MissileConfig
    anti_air_config: AntiAirConfig
    scout_config: ScoutConfig
    token_producer_config: TokenProducerConfig
    token_consumer_config: TokenConsumerConfig

    MAPPING = {
        "id": "itemID",
        "stats_column_id": "statsColumnID",
        "unit_pack": "unitPack",
        "ranking_factor": "rankingFactor",
        "build_time": "buildTime",
        "costs": "costs",
        "daily_costs": "dailyCosts",
        "speeds": "speeds",
        "hit_points": "hitPoints",
        "damage_types": "damageTypes",
        "damage_area": "damageArea",
        "strength": "strength",
        "defense": "defense",
        "ranges": "ranges",
        "view_widths": "viewWidths",
        "required_upgrades": "requiredUpgrades",
        "required_researches": "requiredResearches",
        "unit_cap_research_items": "unitCapResearchItems",
        "friendly_speed_factor": "friendlySpeedFactor",
        "foreign_speed_factor": "foreignSpeedFactor",
        "identifier": "identifier",
        "minimum_tech_level": "minimumTechLevel",
        "unit_features": "unitFeatures",
        "size_factors": "sizeFactors",
        "images": "images",
        "attack_painter": "attackPainter",
        "pin_painter": "pinPainter",
        "unit_class": "unitClass",
        "set": "set",
        "type_size_name": "typeSizeName",
        "controllable_config": "controllableConfig",
        "format_name_small": "formatNameSmall",
        "format_name_big": "formatNameBig",
        "unit_description": "unitDesc",
        "name_faction1": "nameFaction1",
        "name_faction2": "nameFaction2",
        "name_faction3": "nameFaction3",
        "name_faction4": "nameFaction4",
        "type_name": "typeName",
        "unit_moral_impact_factor": "unitMoralImpactFactor",
    }