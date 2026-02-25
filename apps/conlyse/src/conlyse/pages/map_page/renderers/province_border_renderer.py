from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np
from conflict_interface.data_types.map_state.map import Map as MapData

from conlyse.logger import get_logger
from conlyse.pages.map_page.constants import PROVINCE_BORDER_LINE_COLOR
from conlyse.pages.map_page.constants import PROVINCE_BORDER_LINE_WIDTH
from conlyse.pages.map_page.renderers.world_line_renderer import WorldLineRenderer

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map

logger = get_logger()

class ProvinceBorderRenderer(WorldLineRenderer):
    def __init__(self, map_widget: Map):
        super().__init__(map_widget)

    def build_vertex_data(self, map_data: MapData):
        """Build line segment vertex data for province borders"""
        logger.debug(f"Building vertex data for province borders")
        locations = map_data.static_map_data.locations
        vertices = []
        processed_segments = set()

        # Build simple line segments - geometry shader will handle width in screen space
        for location in locations:
            border_points = location.borders
            num_points = len(border_points)
            for i in range(num_points):
                origin = border_points[i]
                point = border_points[(i + 1) % num_points]  # Wrap around to first point

                segment = tuple(
                    sorted([(origin.x, origin.y), (point.x, point.y)])
                )
                if segment in processed_segments:
                    continue
                processed_segments.add(segment)

                # Store as simple line segments (2 vertices per line)
                vertices.extend([origin.x, origin.y, point.x, point.y])

        self.vertices = np.array(vertices, dtype=np.float32)

    def render(self):
        super().render_lines(PROVINCE_BORDER_LINE_COLOR, PROVINCE_BORDER_LINE_WIDTH)
