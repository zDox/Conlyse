from dataclasses import dataclass
from typing import Union

from shapely.geometry import Polygon
from shapely.strtree import STRtree

from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from .custom_types import ArrayList
from .map_state.b64_decoder import decode_connections
from .map_state.b64_decoder import graph
from .map_state.province import Province
from .map_state.triangulation import Triangulation
from .point import Point
from .version import VERSION


@conflict_serializable(SerializationCategory.STATIC_MAP_DATA, version = VERSION)
@dataclass
class StaticMapData(GameObject):
    locations: ArrayList[Province]
    connections_b64: str
    overlap_x: int
    use_minimal_localization: bool
    map_id: str
    day_of_game: int
    connections_v2: str
    height: int
    width: int
    is_reduced: bool
    use_population: bool
    population_factor: float
    triangulations: Triangulation
    version: int


    _encoded_connections: list[dict[str, Union[int, Point]]] = None
    _graph: dict[Point, list[Point]] = None
    _point_to_province: dict[Point, int] = None
    _province_to_points: dict[int, list[Point]] = None
    _str_tree: STRtree = None
    _polygons: list[Polygon] = None

    _province_to_location: dict[int, Province] = None

    MAPPING = {
        "locations": "locations",
        "connections_b64": "connections",
        "overlap_x": "overlapX",
        "use_minimal_localization": "useMinimalLocalization",
        "map_id": "mapID",
        "day_of_game": "dayOfGame",
        "connections_v2": "connections_v2",
        "height": "height",
        "width": "width",
        "is_reduced": "isReduced",
        "use_population": "usePopulation",
        "population_factor": "populationFactor",
        "triangulations": "triangulations",
        "version": "version"
    }

    @property
    def connections(self) -> list[dict[str, Union[int, Point]]]:
        if self._encoded_connections is None:
            self.init_graph()
        return self._encoded_connections

    @property
    def graph(self) -> dict[Point, list[Point]]:
        if self._graph is None:
            self.init_graph()
        return self._graph

    @property
    def str_tree(self) -> tuple[STRtree, list[Polygon]]:
        if self._str_tree is None:
            self._str_tree, self._polygons = compute_str_tree(self.locations)
        return self._str_tree, self._polygons

    @property
    def province_to_location(self) -> dict[int, Province]:
        if self._province_to_location is None:
            self.setup_locations_cache()
        return self._province_to_location

    def init_graph(self):
        if self._encoded_connections is None:
            self._encoded_connections = decode_connections(self.connections_b64)
        self._graph, self._province_to_points,self._point_to_province = graph(self._encoded_connections)

    def get_province(self, point: Point) -> int:
        if self._encoded_connections is None:
            self.init_graph()
        return self._point_to_province.get(point)

    def get_points(self, province: int) -> list[Point]:
        if self._encoded_connections is None:
            self.init_graph()
        return self._province_to_points.get(province)

    def setup_locations_cache(self):
        self._province_to_location = {}
        for province in self.locations:
            self._province_to_location[province.id] = province


def compute_str_tree(locations: ArrayList[Province]) -> tuple[STRtree, list[Polygon]]:
    polygons = []
    for location in locations:
        border = []
        for border_point in location.borders:
            border.append((border_point.x, border_point.y))
        polygons.append(Polygon(border))

    tree = STRtree(polygons)

    return tree, polygons
