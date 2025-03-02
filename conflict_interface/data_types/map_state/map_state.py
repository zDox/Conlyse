from __future__ import annotations

from typing import Union

from .sea_province import SeaProvince



from dataclasses import dataclass

from .province import Province, ProvinceProperty
from .region import Region
from conflict_interface.data_types.common import RegionType
from conflict_interface.data_types.static_map_data import StaticMapData
from ..custom_types import HashMap, HashSet
from ..game_object import GameObject
from ..state import State


@dataclass
class Map(GameObject):
    """
    Represents a map for a game, including information about its properties, configuration, regions,
    and locations.

    This class is responsible for managing various aspects of the game's map, such as its dimensions,
    localization settings, associated regions, and locations. It provides functionality to retrieve
    specific provinces, set static map data, and update map state with new information.

    Attributes:
        is_reduced: Indicates if the map is in a reduced or simplified form.
        version: Represents the version of the map.
        map_id: The unique identifier for the map.
        day_of_game: The current day of the game associated with the map.
        width: Width of the map in game units.
        height: Height of the map in game units.
        use_population: Whether population data is being used in the map.
        use_minimal_localization: Indicates whether minimal localization is applied to the map.
        localized_player_profiles: Determines if player profiles are localized for this map.
        regions: A collection of regions present in the map, categorized by their types.
        overlap_x: Represents horizontal overlap value for certain map representations.
        locations: A set of locations, including both land and sea provinces on the map.
        population_factor: A scaling factor related to population data in the map.
    """
    C = "ultshared.UltMap"
    is_reduced: bool
    version: int
    map_id: str
    day_of_game: int
    width: int
    height: int
    use_population: bool
    use_minimal_localization: bool
    localized_player_profiles: bool
    regions: HashMap[RegionType, Region]
    overlap_x: int
    locations: HashSet[Union[Province, SeaProvince]]
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
    # TODO Precompute dictionary
    def get_province(self, province_id):
        for location in self.locations:
            if location.province_id == province_id:
                return location

    def set_static_map_data(self, static_map_data: StaticMapData):
        for province in static_map_data.locations:
            self.get_province(province.id).set_static_province(province)

    def update(self, new_state):
        for province in new_state.provinces:
            self.get_province(province.province_id).update(province)

@dataclass
class MapState(State):
    """
    Represents the state of a map within a game.

    This class is used to store and manage the state of the map and player-owned
    provinces within the context of the game.
    """
    C = "ultshared.UltMapState"
    STATE_TYPE = 3
    map: Map
    # Provinces which are owned by the current player
    properties: HashMap[int, ProvinceProperty]

    change_set: bool

    MAPPING = {
        "map": "map",
        "properties": "properties",
        "change_set": "changeSet"
    }