from dataclasses import dataclass
from typing import Optional

from .terrain_type import TerrainType
from ..game_object import GameObject
from ..point import Point


@dataclass
class SeaProvince(GameObject):
    """
    Rivers, CostalRegions and HighSea provinces are SeaProvinces.
    """
    C = "ultshared.UltSeaProvince"
    id: int
    name: str
    center_coordinate: Point
    terrain_type: TerrainType
    border: str
    hostility: int
    aggression_level: int # TODO check if pal is the same as aggression_level
    exploration_difficulty: int
    legal_owner: Optional[int]
    resource_production: Optional[int]

    static_data = None

    def __hash__(self):
        return hash(self.id)

    MAPPING = {
        "id": "id",
        "name": "n",
        "center_coordinate": "c",
        "terrain_type": "tt",
        "border": "b",
        "hostility": "hst",
        "aggression_level": "pal",
        "exploration_difficulty": "ed",
        "legal_owner": "lo",
        "resource_production": "rp",

    }

    def set_static_province(self, obj):
        self.static_data = obj