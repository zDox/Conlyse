from dataclasses import dataclass

from conflict_interface.game_object.decorators import conflict_serializable
from ..version import VERSION
from conflict_interface.game_object.game_object import GameObject
from conflict_interface.game_object.game_object_binary import SerializationCategory


@conflict_serializable(SerializationCategory.DATACLASS, version = VERSION)
@dataclass
class Triangulation(GameObject):
    border_triangulations: list[list[dict[str, list[int]]]]
    precision: int
    province_ids: list[int]
    province_bounds: list[int]
    map_bounds: dict[str, int]
    safe_region: dict[str, int]
    province_sizes: dict[str, int]
    version: int
    MAPPING = {
        "border_triangulations": "borderTriangulations",
        "precision": "precision",
        "province_bounds": "provinceBounds",
        "map_bounds": "mapBounds",
        "safe_region": "safeRegion",
        "province_sizes": "provinceSizes",
        "version": "version",
        "province_ids": "provinceIds",
    }
