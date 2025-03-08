from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.map_state.map_state_enums import TerrainType
from conflict_interface.data_types.point import Point


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
    border: str
    hostility: int
    aggression_level: int # TODO check if pal is the same as aggression_level
    exploration_difficulty: int
    legal_owner: Optional[int]
    resource_production: Optional[int]

    static_data = None

    MAPPING = {
        "province_id": "id",
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

    __hash__ = GameObject.__hash__