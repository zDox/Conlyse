from __future__ import annotations

from typing import TYPE_CHECKING

from dataclasses import dataclass
from typing import Union

from conflict_interface.data_types.custom_types import ArrayList
from conflict_interface.data_types.map_state.b64_decoder import decode_connections
from conflict_interface.data_types.map_state.b64_decoder import graph
from conflict_interface.data_types.map_state.static_province import StaticProvince
from conflict_interface.data_types.point import Point

from conflict_interface.data_types.game_object import GameObject


@dataclass
class StaticMapData(GameObject):
    locations: ArrayList[StaticProvince]
    connections_b64: str

    _encoded_connections: list[dict[str, Union[int, Point]]] = None

    MAPPING = {
        "locations": "locations",
        "connections_b64": "connections",
    }

    @property
    def connections(self) -> list[dict[str, Union[int, Point]]]:
        if self._encoded_connections is None:
            self._encoded_connections = decode_connections(self.connections_b64)
        return self._encoded_connections

    @property
    def graph(self) -> dict[Point, list[Point]]:
        if self._encoded_connections is None:
            self._encoded_connections = decode_connections(self.connections_b64)
        return graph(self._encoded_connections)[0]

    def get_province(self, point: Point) -> int:
        if self._encoded_connections is None:
            self._encoded_connections = decode_connections(self.connections_b64)
        return graph(self._encoded_connections)[1].get(point)

    def get_points(self, province: int) -> list[Point]:
        if self._encoded_connections is None:
            self._encoded_connections = decode_connections(self.connections_b64)
        return graph(self._encoded_connections)[2].get(province)


