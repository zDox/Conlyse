from dataclasses import dataclass

from .terrain_type import TerrainType
from conflict_interface.utils import GameObject, Point


@dataclass
class SeaProvince(GameObject):
    C = "ultshared.UltSeaProvince"
    province_id: int
    name: str
    center_coordinate: Point
    terrain_type: TerrainType

    def __hash__(self):
        return hash(self.province_id)

    MAPPING = {
        "province_id": "id",
        "name": "n",
        "center_coordinate": "c",
        "terrain_type": "tt",
    }

    def set_static_province(self, obj):
        pass