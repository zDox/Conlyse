from dataclasses import dataclass
from typing import Optional
from typing import Union

import numpy as np
from shapely import Point as ShapelyPoint

from .land_province import LandProvince
from .sea_province import SeaProvince
from ..common.enums.region_type import RegionType
from ..custom_types import HashMap
from ..custom_types import HashSet
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..map_state.region import Region
from ..point import Point
from ..static_map_data import StaticMapData

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
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
    regions: Optional[HashMap[RegionType, Region]]
    overlap_x: int
    population_factor: int
    locations: HashSet[Union[LandProvince, SeaProvince]]

    _province_id_to_index: dict[int, int] = None
    _provinces: dict[int, Union[LandProvince, SeaProvince]] = None
    static_map_data: StaticMapData = None

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

    @property
    def provinces(self) -> dict[int, LandProvince | SeaProvince]:
        if not self._provinces:
            self._provinces = {
                province.id: province
                for province in self.locations
            }
        return self._provinces

    def province_id_to_index(self, province_id: int) -> int | None:
        if not self._province_id_to_index:
            self._province_id_to_index = {}
            for i, province in enumerate(self.locations):
                self._province_id_to_index[province.id] = i
        return self._province_id_to_index.get(province_id)

    def province_index_to_id(self, index: int) -> int | None:
        if index < 0 or index >= len(self.locations):
            return None
        return self.locations[index].id

    def clear_cache(self):
        self._province_id_to_index = None
        self._provinces = None

    def set_static_map_data(self, static_map_data: StaticMapData):
        self.static_map_data = static_map_data

    def get_connections(self) -> list[dict[str, Union[int, Point]]]:
        return self.static_map_data.connections

    def get_graph(self) -> dict[Point, list[Point]]:
        return self.static_map_data.graph

    def get_province_id_from_point(self, point_to_check: Point) -> int:
        static_map = self.game.game_state.states.map_state.map.static_map_data
        sh_point = ShapelyPoint(point_to_check.x, point_to_check.y)
        tree, polygons = static_map.str_tree

        province_id = None
        candidate_indices = tree.query(sh_point)
        for idx in candidate_indices:
            polygon = polygons[idx]
            if polygon.contains(sh_point):
                province_id = static_map.locations[idx].id
                break

        return province_id

    def get_closest_point_on_nearest_connection(self, point_to_check: Point) -> Point:

        static_map = self.game.game_state.states.map_state.map.static_map_data
        province_id = self.get_province_id_from_point(point_to_check)
        relevant_points = static_map.get_points(province_id)
        adj = static_map.graph

        min_dist = float("inf")
        closest = None

        for start in relevant_points:
            for end in adj[start]:
                pos = np.array([point_to_check.x, point_to_check.y])
                a = np.array([start.x, start.y])
                b = np.array([end.x, end.y])

                ab = b - a
                ap = pos - a

                ab_norm = np.dot(ap, ab) / np.dot(ab, ab)

                ab_norm = max(0, min(1, ab_norm))

                c = a + ab * ab_norm

                d = np.linalg.norm(pos - c)

                if d < min_dist:
                    min_dist = d
                    c_x, c_y = c
                    closest = Point(float(c_x), float(c_y))

        return closest