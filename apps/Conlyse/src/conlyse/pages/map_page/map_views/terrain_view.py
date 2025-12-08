# terrain_view.py
import numpy as np
from conflict_interface.data_types.map_state.map_state_enums import TerrainType
from conflict_interface.data_types.map_state.province import Province

from conlyse.pages.map_page.map_views.map_view import MapView

TERRAIN_TYPE_TO_RGB = {
    TerrainType.NONE: (255, 0, 255),
    TerrainType.PLAINS: (34, 139, 34),
    TerrainType.HILLS: (139, 69, 19),
    TerrainType.MOUNTAIN: (139, 137, 137),
    TerrainType.FOREST: (34, 100, 34),
    TerrainType.URBAN: (169, 169, 169),
    TerrainType.JUNGLE: (0, 100, 0),
    TerrainType.TUNDRA: (176, 196, 222),
    TerrainType.DESERT: (210, 180, 140),
    TerrainType.SEA: (0, 0, 255),
    TerrainType.HIGHSEA: (25, 25, 112),
    TerrainType.COASTAL: (70, 130, 180),
    TerrainType.SUBURBAN: (192, 192, 192),
}


class TerrainView(MapView):
    """
    Terrain map view that colors provinces based on their terrain type.

    Each terrain type (plains, hills, mountains, etc.) is assigned a distinct
    color to help visualize the geographic features of the game world.
    """
    def build_color_data(self):
        self.color_data = self._init_color_array()

        for province in self.ritf.get_provinces().values():
            r, g, b = TERRAIN_TYPE_TO_RGB.get(province.terrain_type, (255, 0, 255))
            self.color_data[province.id] = (r, g, b, 255)

    def update_province(self, province: Province, changed_attributes: dict):
        if 'terrain_type' in changed_attributes:
            r, g, b = TERRAIN_TYPE_TO_RGB.get(province.terrain_type, (255, 0, 255))
            self.set_province_color(province.id, (r, g, b, 255))