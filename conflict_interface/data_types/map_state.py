from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from conflict_interface.game_interface import GameInterface
from conflict_interface.utils import GameObject, HashMap

from dataclasses import dataclass

from .province import Province, ProvinceProperty
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

@dataclass
class MapState(GameObject):
    STATE_ID = 3
    map: Map
    # Provinces which are owned by the current player
    properties: HashMap[int, ProvinceProperty]

    def update(self, new_state):
        for province in new_state.provinces:
            self.provinces[province.province_id].update(province)

    def set_static_map_data(self, static_map_data: StaticMapData):
        for province in static_map_data.provinces:
            self.provinces[province.id].set_static_province(province)
