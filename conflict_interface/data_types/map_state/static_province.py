from dataclasses import dataclass

from conflict_interface.data_types.common.enums.region_type import RegionType
from conflict_interface.data_types.game_object import GameObject
from conflict_interface.data_types.game_object_binary import SerializationCategory
from conflict_interface.data_types.decorators import binary_serializable
from conflict_interface.data_types.map_state.b64_decoder import decode_border
from conflict_interface.data_types.map_state.map_state_enums import TerrainType
from conflict_interface.data_types.point import Point

@binary_serializable(SerializationCategory.DATACLASS)
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




