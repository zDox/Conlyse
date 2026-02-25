from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from conflict_interface.data_types.newest.map_state.map import  Map as MapData

from conlyse.logger import get_logger
from conlyse.pages.map_page.constants import CONNECTION_LINE_COLOR
from conlyse.pages.map_page.constants import CONNECTION_LINE_WIDTH
from conlyse.pages.map_page.renderers.world_line_renderer import WorldLineRenderer

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map

logger = get_logger()

script_dir = Path(__file__).parent



class ProvinceConnectionRenderer(WorldLineRenderer):
    def __init__(self, map_widget: Map):
        super().__init__(map_widget)

    def build_vertex_data(self, map_data: MapData):
        """Build line segment vertex data for connections (width handled in shader)"""
        logger.debug(f"Building vertex data for province connections")
        graph = map_data.static_map_data.graph
        vertices = []
        processed_segments = set()

        # Build simple line segments - geometry shader will handle width in screen space
        for origin, points in graph.items():
            for point in points:
                segment = tuple(sorted([(origin.x, origin.y), (point.x, point.y)]))
                if segment in processed_segments:
                    continue
                processed_segments.add(segment)

                # Store as simple line segments (2 vertices per line)
                vertices.extend([origin.x, origin.y, point.x, point.y])

        logger.debug(f"Built {len(vertices) // 4} line segments for province connections")
        self.vertices = np.array(vertices, dtype=np.float32)

    def render(self):
        super().render_lines(CONNECTION_LINE_COLOR, CONNECTION_LINE_WIDTH)