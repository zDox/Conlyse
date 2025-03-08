from dataclasses import dataclass
from typing import Union

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.map_state.b64_decoder import decode_connections
from conflict_interface.data_types.map_state.b64_decoder import graph
from conflict_interface.data_types.map_state.static_province import StaticProvince
from conflict_interface.data_types.point import Point

from conflict_interface.data_types.game_object import GameObject

from shapely.geometry import Polygon
from shapely.strtree import STRtree


@dataclass
class StaticMapData(GameObject):
    locations: ArrayList[StaticProvince]
    connections_b64: str

    _encoded_connections: list[dict[str, Union[int, Point]]] = None
    _graph: dict[Point, list[Point]] = None
    _point_to_province: dict[Point, int] = None
    _province_to_points: dict[int, list[Point]] = None
    _str_tree: STRtree = None
    _polygons: list[Polygon] = None

    MAPPING = {
        "locations": "locations",
        "connections_b64": "connections",
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

    def init_graph(self):
        if self._encoded_connections is None:
            self._encoded_connections = decode_connections(self.connections_b64)
        self._graph, self._province_to_points,self._point_to_province = graph(self._encoded_connections)

    @property
    def str_tree(self) -> tuple[STRtree, list[Polygon]]:
        if self._str_tree is None:
            self._str_tree, self._polygons = compute_str_tree(self.locations)
        return self._str_tree, self._polygons

    def get_province(self, point: Point) -> int:
        if self._encoded_connections is None:
            self.init_graph()
        return self._point_to_province.get(point)

    def get_points(self, province: int) -> list[Point]:
        if self._encoded_connections is None:
            self.init_graph()
        return self._province_to_points.get(province)


def compute_str_tree(locations: ArrayList[StaticProvince]) -> tuple[STRtree, list[Polygon]]:
    polygons = []
    for location in locations:
        border = []
        for border_point in location.borders:
            border.append((border_point.x, border_point.y))
        polygons.append(Polygon(border))

    tree = STRtree(polygons)

    return tree, polygons
