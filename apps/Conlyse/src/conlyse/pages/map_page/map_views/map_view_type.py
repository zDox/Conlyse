from enum import Enum

from conlyse.pages.map_page.map_views.political_view import PoliticalView
from conlyse.pages.map_page.map_views.resource_view import ResourceView
from conlyse.pages.map_page.map_views.terrain_view import TerrainView


class MapViewType(Enum):
    POLITICAL = PoliticalView
    TERRAIN = TerrainView
    RESOURCE = ResourceView