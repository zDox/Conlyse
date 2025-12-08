from enum import Enum

from conlyse.pages.map_page.map_views.political_view import PoliticalView
from conlyse.pages.map_page.map_views.terrain_view import TerrainView


class MapViewType(Enum):
    POLITICAL = 1
    TERRAIN = 2

MAPVIEWTYPE_TO_CLASS = {
    MapViewType.POLITICAL: PoliticalView,
    MapViewType.TERRAIN: TerrainView
}