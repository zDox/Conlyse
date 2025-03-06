from __future__ import annotations

from collections import defaultdict
from typing import Optional
from typing import Union




from dataclasses import dataclass
from typing import get_type_hints
from typing import override

from conflict_interface.data_types.map_state.province import logger
from conflict_interface.data_types.point import Point
from conflict_interface.data_types.map_state.province import Province
from conflict_interface.data_types.map_state.region import Region
from conflict_interface.data_types.map_state.sea_province import SeaProvince
from conflict_interface.data_types.custom_types import HashMap, HashSet
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.common import RegionType
from conflict_interface.data_types.map_state.province_property import ProvinceProperty
from conflict_interface.data_types.state import State
from conflict_interface.data_types.static_map_data import StaticMapData
from conflict_interface.utils.helper import safe_issubclass

from shapely.geometry import Point as shapely_point
import numpy as np


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
    locations: HashSet[Union[Province, SeaProvince]]
    population_factor: int

    static_map_data: StaticMapData = None

    _provinces: dict[int, Union[Province, SeaProvince]] = None

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
        self.static_map_data = static_map_data
        for province in static_map_data.locations:
            self.get_province(province.id).set_static_province(province)

    def get_connections(self) -> list[dict[str, Union[int, Point]]]:
        return self.static_map_data.connections

    def get_province_id_from_point(self, point_to_check: Point) -> int:
        static_map = self.game.game_state.states.map_state.map.static_map_data
        sh_point = shapely_point(point_to_check.x, point_to_check.y)
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

    @override
    def update(self, other: GameObject):
        if self._provinces is None:
            self._provinces = defaultdict()

        if not isinstance(other, Map):
            raise ValueError("UPDATE ERROR: Cannot update Map with object of type: " + str(type(other)))

        for key in self.get_mapping().keys():
            if getattr(other, key) is None:
                continue
            elif safe_issubclass(get_type_hints(type(self))[key], GameObject):
                if getattr(self, key) is None:
                    setattr(self, key, getattr(other, key))
                getattr(self, key).update(getattr(other, key))
            elif key not in ("locations", ):
                setattr(self, key, getattr(other, key))

        if other.locations is not None:
            for location in other.locations:
                if location.province_id in self._provinces.keys():
                    self._provinces[location.province_id].update(location)
                else:
                    logger.warning(f"New province found: {location.province_id}")
                    self.locations.add(location)
                    self._provinces[location.province_id] = location


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

    @override
    def update(self, other: GameObject):
        if not isinstance(other, MapState):
            raise ValueError("UPDATE ERROR: Cannot update MapState with object of type: " + str(type(other)))

        if other.map is not None:
            self.map.update(other.map)

        if other.properties is not None:
            for province_id, prop in other.properties.items():
                if province_id in self.properties:
                    if self.properties[province_id] is None:
                        self.properties[province_id] = prop
                    self.properties[province_id].update(prop)
                else:
                    self.properties[province_id] = prop

