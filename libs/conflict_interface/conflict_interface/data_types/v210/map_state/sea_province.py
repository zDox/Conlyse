from dataclasses import dataclass
from typing import Optional

from conflict_interface.game_object.decorators import conflict_serializable
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from .b64_decoder import decode_border
from ..common.enums.region_type import RegionType
from ..map_state.map_state_enums import TerrainType
from ..point import Point
from ..version import VERSION


@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class SeaProvince(GameObject):
    """
    Rivers, CostalRegions and HighSea provinces are SeaProvinces.
    """
    C = "ultshared.UltSeaProvince"
    id: int
    name: Optional[str]
    center_coordinate: Point
    terrain_type: TerrainType
    hostility: int
    aggression_level: int # TODO check if pal is the same as aggression_level
    exploration_difficulty: int
    legal_owner: Optional[int]
    resource_production: Optional[int]

    borders_base_64: Optional[str]
    border_type_64: Optional[str]
    region: list[RegionType] = None

    _encoded_borders: list[Point] = None

    MAPPING = {
        "id": "id",
        "name": "n",
        "center_coordinate": "c",
        "terrain_type": "tt",
        "hostility": "hst",
        "aggression_level": "pal",
        "exploration_difficulty": "ed",
        "legal_owner": "lo",
        "resource_production": "rp",
        "region": "rg",
        "borders_base_64": "b",
        "border_type_64": "bt",
    }

    @property
    def borders(self) -> list[Point]:
        if self._encoded_borders is None:
            self._encoded_borders = decode_border(self.borders_base_64)
        return self._encoded_borders

    __hash__ = GameObject.__hash__