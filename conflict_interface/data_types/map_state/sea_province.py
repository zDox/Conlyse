from dataclasses import dataclass

from .terrain_type import TerrainType
from ..game_object import GameObject
from ..point import Point


@dataclass
class SeaProvince(GameObject):
    """
    Rivers, CostalRegions and HighSea provinces are SeaProvinces.
    """
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