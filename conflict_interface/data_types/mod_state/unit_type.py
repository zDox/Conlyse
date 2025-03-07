

from dataclasses import dataclass
from typing import Set
from typing import Union

from conflict_interface.data_types.resource_state.resource_types import ResourceType
from conflict_interface.data_types.custom_types import DateTimeMillisecondsInt
from conflict_interface.data_types.custom_types import HashMap
from conflict_interface.data_types.custom_types import TimeDeltaMillisecondsInt
from conflict_interface.data_types.custom_types import TimeDeltaSecondsInt
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.mod_state.configuration import AirMobileConfig
from conflict_interface.data_types.mod_state.configuration import ArmyBoostConfig
from conflict_interface.data_types.mod_state.configuration import ConflictCondition
from conflict_interface.data_types.mod_state.configuration import ConvertToResourceConfig
from conflict_interface.data_types.mod_state.configuration import DiplomaticAggressionConfig
from conflict_interface.data_types.mod_state.configuration import DisbandConfig
from conflict_interface.data_types.mod_state.configuration import DummyMissileConfig
from conflict_interface.data_types.mod_state.configuration import DummyScoutConfig
from conflict_interface.data_types.mod_state.configuration import LaunchTargetConfig
from conflict_interface.data_types.mod_state.configuration import LimitedMobilizationConfig
from conflict_interface.data_types.mod_state.configuration import MissileCarrierConfig, DummyMissileCarrierConfig
from conflict_interface.data_types.mod_state.configuration import \
        MissileConfig, SortingConfig, SoundConfig, AirplaneConfig, \
        ControllableConfig, CarrierConfig, AntiAirConfig, ScoutConfig, \
        TokenProducerConfig, TokenConsumerConfig


from typing import Optional

from conflict_interface.data_types.mod_state.configuration import RadarConfig
from conflict_interface.data_types.mod_state.configuration import RadarSignatureConfig
from conflict_interface.data_types.mod_state.configuration import RenderConfig
from conflict_interface.data_types.mod_state.configuration import StackingConfig
from conflict_interface.data_types.mod_state.configuration import TokenSensitivityConfig
from conflict_interface.data_types.mod_state.configuration import UnitTypeFrontEndConfig
from conflict_interface.data_types.player_state.faction import Faction
from conflict_interface.data_types.research_state.research_type import ResearchType


@dataclass
class UnitType(GameObject):
    """

    """
    C = "ultshared.warfare.UltUnitType"
    id: int
    stats_column_id: int
    unit_pack: int
    ranking_factor: float
    build_time: TimeDeltaMillisecondsInt
    costs: HashMap[ResourceType, float]
    daily_costs: HashMap[ResourceType, float]
    speeds: HashMap[int, float]
    hit_points: HashMap[int, float]
    damage_types: HashMap[int, float]
    damage_area: HashMap[int, float] # Corresponds to the damage weight in other mentioned documents
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
    unit_features: Optional[HashMap[int, float]] # TODO Key should be UnitFeature
    size_factors: Optional[HashMap[int, float]]
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
    type_size_name: str
    sort_value: int
    producible: bool
    unit_moral_impact_factor: float
    images: HashMap[str, str] # TODO check tpyes
    unit_name: str

    diplomatic_aggression_config: DiplomaticAggressionConfig
    air_mobile_config: AirMobileConfig
    army_boost_config: ArmyBoostConfig
    limited_mobilization_config: LimitedMobilizationConfig
    controllable_config: Optional[ControllableConfig]
    carrier_config: Optional[CarrierConfig]
    missile_config: Union[MissileConfig, DummyMissileConfig]
    anti_air_config: AntiAirConfig
    sorting_config: SortingConfig
    sound_config: SoundConfig
    airplane_config: AirplaneConfig
    scout_config: Union[ScoutConfig, DummyScoutConfig]
    token_producer_config: TokenProducerConfig
    token_consumer_config: TokenConsumerConfig
    missile_carrier_config: Union[MissileCarrierConfig, DummyMissileCarrierConfig]
    radar_signature_config: Optional[RadarSignatureConfig]
    radar_config: Optional[RadarConfig]
    convert_to_resource_config: Optional[ConvertToResourceConfig]
    disband_config: Optional[DisbandConfig]
    stacking_config: StackingConfig
    launch_target_config: LaunchTargetConfig
    token_sensitivity_config: TokenSensitivityConfig
    production_requirements_config: ConflictCondition
    frontend_config: UnitTypeFrontEndConfig
    render_config: RenderConfig

    _tier: int = None
    _is_max_tier: int = None
    _factions: Set[Faction] = None


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
        "defense": "defence",
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
        "attack_painter": "attackPainter",
        "pin_painter": "pinPainter",
        "unit_class": "unitClass",
        "set": "set",
        "type_size_name": "typeSizeName",
        "controllable_config": "controllableConfig",
        "formation_name_small": "formationNameSmall",
        "formation_name_big": "formationNameBig",
        "unit_description": "unitDesc",
        "name_faction1": "nameFaction1",
        "name_faction2": "nameFaction2",
        "name_faction3": "nameFaction3",
        "name_faction4": "nameFaction4",
        "type_name": "typeName",
        "unit_moral_impact_factor": "unitMoraleImpactFactor",
        "sort_value": "sortValue",
        "producible": "producible",
        "sorting_config": "sortingConfig",
        "sound_config": "soundConfig",
        "airplane_config": "airplaneConfig",
        "carrier_config": "carrierConfig",
        "missile_config": "missileConfig",
        "anti_air_config": "antiAirConfig",
        "scout_config": "scoutConfig",
        "token_producer_config": "tokenProducerConfig",
        "token_consumer_config": "tokenConsumerConfig",
        "missile_carrier_config": "missileCarrierConfig",
        "diplomatic_aggression_config": "diplomaticAggressionConfig",
        "air_mobile_config": "airmobile",
        "army_boost_config": "armyBoostConfig",
        "limited_mobilization_config": "limitedMobilizationConfig",
        "images": "images",
        "unit_name": "unitName",
        "radar_signature_config": "radarSignatureConfig",
        "radar_config": "radarConfig",
        "convert_to_resource_config": "convertToResourceConfig",
        "disband_config": "disbandConfig",
        "stacking_config": "stackingConfig",
        "launch_target_config": "launchTargetConfig",
        "token_sensitivity_config": "tokenSensitivityConfig",
        "production_requirements_config": "productionRequirementConfig",
        "frontend_config": "frontendConfig",
        "render_config": "renderConfig",
    }
    def get_name_with_tier(self):
        """
        Returns the name of the unit, including its tier if applicable.
        Tier 1 units at maximum tier will not have the tier displayed.
        """
        if self.tier == 1 and self.is_maximum_tier():
            return self.unit_name
        else:
            return f"{self.unit_name} Lvl. {self.tier}"

    @property
    def tier(self):
        """
        Returns the tier of the unit, calculating it if necessary.
        If there are no required researches, defaults to Tier 1.
        """
        if self._tier is None:
            required_research = self.get_required_research_type()
            self._tier = max(1, required_research.tier if required_research else 1)
        return self._tier

    def is_maximum_tier(self):
        """
        Determines if this unit is at its maximum tier.
        A unit is at max tier if it has no further replaceable research.
        """
        if self._is_max_tier is None:
            required_research = self.get_required_research_type()
            self._is_max_tier = not required_research.can_be_replaced() if required_research else True
        return self._is_max_tier

    def get_required_research_type(self) -> ResearchType | None:
        """
        Returns the research type required for this unit.
        If multiple researches are required, it retrieves the first one.
        """
        if self.required_researches:
            research_key = list(self.required_researches)[0]
            return self.game.game_state.states.mod_state.research_types.get(research_key)
        return None

    def get_level_marker(self):
        """
        Returns the level marker of the unit.
        If the tier is greater than 1 and the unit is at its maximum tier, it returns "max".
        Otherwise, it simply returns the tier.
        """
        tier = self.tier
        return "max" if tier > 1 and self.is_maximum_tier() else tier

    @property
    def factions(self):
        if self._factions is None:
            self._factions = set()
            research = self.get_required_research_type()
            if research:
                self._factions.update(research.faction_specific_config.factions)
        return self._factions

    def has_faction(self, faction: Faction):
        return faction in self.factions