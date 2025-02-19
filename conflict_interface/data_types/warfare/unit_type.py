
from conflict_interface.utils import GameObject, MappedValue

from dataclasses import dataclass
from datetime import timedelta

from conflict_interface.data_types.modding.configuration import \
        MissileConfig, SortingConfig, SoundConfig, AirplaneConfig, \
        ControllableConfig, CarrierConfig, AntiAirConfig, ScoutConfig, \
        TokenProducerConfig, TokenConsumerConfig

from .unit_feature import UnitFeature
from ...utils.json_mapped_class import JavaTypes


@dataclass
class UnitType(GameObject):
    id: int
    stats_column_id: int
    unit_pack: int
    ranking_factor: int
    build_time: timedelta
    costs: dict[int, float]
    daily_costs: dict[int, float]
    speeds: dict[int, float]
    hit_points: dict[int, float]
    damage_types: dict[int, float]
    damage_area: dict[int, float]
    strength: dict[int, float]
    defense: dict[int, float]
    ranges: dict[int, float]
    view_widths: dict[int, float]
    required_upgrades: dict[int, int]
    required_researches: dict[int, int]
    unit_cap_research_items: dict[int, int]
    friendly_speed_factor: float
    foreign_speed_factor: float
    identifier: str
    minimum_tech_level: int
    unit_features: dict[UnitFeature, float]
    size_factors: dict[int, float]
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
        "costs": MappedValue("costs", type=JavaTypes.HashMap),
        "daily_costs": MappedValue("dailyCosts", type=JavaTypes.HashMap),
        "speeds": MappedValue("speeds", type=JavaTypes.HashMap),
        "hit_points": MappedValue("hitPoints", type=JavaTypes.HashMap),
        "damage_types": MappedValue("damageTypes", type=JavaTypes.HashMap),
        "damage_area": MappedValue("damageArea", type=JavaTypes.HashMap),
        "strength": MappedValue("strength", type=JavaTypes.HashMap),
        "defense": MappedValue("defense", type=JavaTypes.HashMap),
        "ranges": MappedValue("ranges", type=JavaTypes.HashMap),
        "view_widths": MappedValue("viewWidths", type=JavaTypes.HashMap),
        "required_upgrades": MappedValue("requiredUpgrades", type=JavaTypes.HashMap),
        "required_researches": MappedValue("requiredResearches", type=JavaTypes.HashMap),
        "unit_cap_research_items": MappedValue("unitCapResearchItems", type=JavaTypes.HashMap),
        "friendly_speed_factor": "friendlySpeedFactor",
        "foreign_speed_factor": "foreignSpeedFactor",
        "identifier": "identifier",
        "minimum_tech_level": "minimumTechLevel",
        "unit_features": MappedValue("unitFeatures", type=JavaTypes.HashMap),
        "size_factors": MappedValue("sizeFactors", type=JavaTypes.HashMap),
        "images": MappedValue("images", type=JavaTypes.HashMap),
        "attack_painter": "attackPainter",
        "pin_painter": "pinPainter",
        "unit_class": "unitClass",
        "set": "set",
        "type_size_name": "typeSizeName",
        "controllable_config": MappedValue("controllableConfig", type=ControllableConfig),
        "format_name_small": "formatNameSmall",
        "format_name_big": "formatNameBig",
        "unit_description": "unitDesc",
        "name_faction1": "nameFaction1",
        "name_faction2": "nameFaction2",
        "name_faction3": "nameFaction3",
        "name_faction4": "nameFaction4",
        "type_name": "typeName",
        "unit_moral_impact_factor": "unitMoralImpactFactor",
        "sorting_config": MappedValue("sortingConfig", type=SortingConfig),
        "sound_config": MappedValue("soundConfig", type=SoundConfig),
        "render_config": MappedValue("renderConfig", type=RenderConfig)
        "airplane_config": MappedValue("airplaneConfig", type=AirplaneConfig),


    }