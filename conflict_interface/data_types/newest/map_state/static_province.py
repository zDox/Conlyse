from dataclasses import dataclass

from ..common.enums.region_type import RegionType
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory
from conflict_interface.game_object.decorators import conflict_serializable
from ..map_state.b64_decoder import decode_border
from ..map_state.map_state_enums import TerrainType
from ..point import Point

from ..version import VERSION
@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class StaticProvince(GameObject):
    """
    Represents a static province within a game context.

    Attributes:
        id: Unique identifier for the province within the game system.
        terrain_type: Type of terrain associated with the province.
        center_coordinate: Geographic center of the province as a point.
        region: List of regions related to the province.
    """
    id: int
    terrain_type: TerrainType
    center_coordinate: Point
    borders_base_64: str
    border_type_64: str
    region: list[RegionType] = None

    _encoded_borders: list[Point] = None

    MAPPING = {
        "id": "id",
        "terrain_type": "tt",
        "center_coordinate": "c",
        "region": "rg",
        "borders_base_64": "b",
        "border_type_64": "bt",
    }

    @property
    def borders(self) -> list[Point]:
        if self._encoded_borders is None:
            self._encoded_borders = decode_border(self.borders_base_64)
        return self._encoded_borders




