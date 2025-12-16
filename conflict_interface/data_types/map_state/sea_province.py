from dataclasses import dataclass
from typing import Optional

from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.game_object_binary import binary_serializable
from conflict_interface.data_types.map_state.map_state_enums import TerrainType
from conflict_interface.data_types.map_state.static_province import StaticProvince
from conflict_interface.data_types.point import Point

@binary_serializable(SerializationCategory.DATACLASS)
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

    _static_data: StaticProvince = None

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

    @property
    def static_data(self) -> StaticProvince:
        if not self._static_data:
            self._static_data = self.game.get_map().static_map_data.province_to_location[self.id]

        return self._static_data

    __hash__ = GameObject.__hash__