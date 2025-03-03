from dataclasses import dataclass

from conflict_interface.data_types import GameObject
from conflict_interface.data_types import TerrainType
from conflict_interface.data_types.common import RegionType
from conflict_interface.data_types.point import Point


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
    region: list[RegionType] = None

    MAPPING = {
        "id": "id",
        "terrain_type": "tt",
        "center_coordinate": "c",
        "region": "rg",
    }
