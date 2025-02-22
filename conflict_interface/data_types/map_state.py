from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    pass
from conflict_interface.utils import GameObject, HashMap, HashSet

from dataclasses import dataclass

from conflict_interface.data_types.province import Province, ProvinceProperty, RegionType, Region
from .static_map_data import StaticMapData

@dataclass
class Map(GameObject):
    is_reduced: bool
    version: int
    map_id: int
    day_of_game: int
    width: int
    height: int
    use_population: bool
    use_minimal_localization: bool
    localized_player_profiles: bool
    regions: HashMap[RegionType, Region]
    overlap_x: int
    locations: HashSet[Province]
    population_factor: int
    MAPPING = {
        "is_reduced": "isReduced",
        "version": "version",
        "map_id": "mapID",
        "day_of_game": "dayOfGame",
        "width": "width",
        "height": "height",
        "use_population": "usePopulation",
        "use_minimal_localization": "useMinimalLocalization",
        "localized_player_profiles": "localizedPlayerProfiles",
        "regions": "regions",
        "overlap_x": "overlapX",
        "locations": "locations",
        "population_factor": "populationFactor"
    }
@dataclass
class MapState(GameObject):
    STATE_ID = 3
    map: Map
    # Provinces which are owned by the current player
    properties: HashMap[int, ProvinceProperty]

    MAPPING = {
        "map": "map",
        "properties": "properties"
    }

    def update(self, new_state):
        for province in new_state.provinces:
            self.provinces[province.province_id].update(province)

    def set_static_map_data(self, static_map_data: StaticMapData):
        for province in static_map_data.provinces:
            self.provinces[province.id].set_static_province(province)
