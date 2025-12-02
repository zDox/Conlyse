"""
Province Renderer
=================
Renders provinces on the map using OpenGL.

Author: Copilot
Date: 2025-12-02
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, List, Tuple

import numpy as np
from OpenGL.GL import (
    glBegin, glEnd, glVertex2f, glColor4f, glLineWidth,
    GL_POLYGON, GL_LINE_LOOP, glEnable, glDisable, glBlendFunc,
    GL_BLEND, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA
)

from conlyse.pages.map_page.entity_renderer import EntityRenderer

if TYPE_CHECKING:
    from conlyse.pages.map_page.camera import Camera


class ProvinceRenderer(EntityRenderer):
    """
    Renders provinces with their borders and colors.
    """

    def __init__(self):
        """Initialize the province renderer."""
        super().__init__()
        self.province_colors: Dict[int, Tuple[float, float, float, float]] = {}

    def initialize(self):
        """Initialize OpenGL resources for province rendering."""
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._initialized = True

    def set_province_color(self, province_id: int, color: Tuple[float, float, float, float]):
        """
        Set the color for a specific province.

        Args:
            province_id: Province ID
            color: RGBA color (values 0-1)
        """
        self.province_colors[province_id] = color

    def _calculate_bounds(self, border_points: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box for a list of points.

        Args:
            border_points: List of (x, y) points

        Returns:
            Tuple of (min_x, max_x, min_y, max_y)
        """
        if not border_points:
            return (0, 0, 0, 0)
        
        x_coords, y_coords = zip(*border_points)
        return (min(x_coords), max(x_coords), min(y_coords), max(y_coords))

    def render(self, camera: Camera, provinces: Dict[int, Any]):
        """
        Render provinces.

        Args:
            camera: Camera for coordinate transformations
            provinces: Dictionary of province_id -> province object
        """
        if not self._initialized:
            return

        visible_rect = camera.get_visible_rect()
        
        # Render province fills
        for province_id, province in provinces.items():
            if not hasattr(province, 'static_data') or not hasattr(province.static_data, 'borders'):
                continue

            # Get province border points
            border_points = [(point.x, point.y) for point in province.static_data.borders]
            
            if not border_points:
                continue

            # Simple culling: check if province might be visible
            min_x, max_x, min_y, max_y = self._calculate_bounds(border_points)
            
            if (max_x < visible_rect[0] or min_x > visible_rect[2] or
                max_y < visible_rect[1] or min_y > visible_rect[3]):
                continue

            # Get color for province
            color = self.province_colors.get(province_id, (0.8, 0.8, 0.8, 0.4))
            
            # Convert to screen coordinates
            screen_points = [camera.world_to_screen(p) for p in border_points]
            
            # Render filled polygon
            glColor4f(*color)
            glBegin(GL_POLYGON)
            for sx, sy in screen_points:
                glVertex2f(sx, sy)
            glEnd()

        # Render province borders (outlines)
        glColor4f(0.0, 0.0, 0.0, 1.0)  # Black borders
        glLineWidth(1.0)
        
        for province_id, province in provinces.items():
            if not hasattr(province, 'static_data') or not hasattr(province.static_data, 'borders'):
                continue

            border_points = [(point.x, point.y) for point in province.static_data.borders]
            
            if not border_points:
                continue

            # Simple culling
            min_x, max_x, min_y, max_y = self._calculate_bounds(border_points)
            
            if (max_x < visible_rect[0] or min_x > visible_rect[2] or
                max_y < visible_rect[1] or min_y > visible_rect[3]):
                continue

            # Convert to screen coordinates
            screen_points = [camera.world_to_screen(p) for p in border_points]
            
            # Render border
            glBegin(GL_LINE_LOOP)
            for sx, sy in screen_points:
                glVertex2f(sx, sy)
            glEnd()

    def cleanup(self):
        """Clean up OpenGL resources."""
        self.province_colors.clear()
        self._initialized = False


def get_distinct_color(index: int, total: int) -> Tuple[float, float, float, float]:
    """
    Generate a distinct color for a given index.

    Args:
        index: Index of the color
        total: Total number of colors needed

    Returns:
        RGBA color tuple (values 0-1)
    """
    if total == 0:
        return (0.5, 0.5, 0.5, 0.4)
    
    # Use golden ratio for good color distribution
    golden_ratio = 0.618033988749895
    hue = (index * golden_ratio) % 1.0
    
    # Convert HSV to RGB (S=0.7, V=0.9 for nice colors)
    h = hue * 6.0
    c = 0.7 * 0.9
    x = c * (1 - abs((h % 2) - 1))
    m = 0.9 - c
    
    if h < 1:
        r, g, b = c, x, 0
    elif h < 2:
        r, g, b = x, c, 0
    elif h < 3:
        r, g, b = 0, c, x
    elif h < 4:
        r, g, b = 0, x, c
    elif h < 5:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    return (r + m, g + m, b + m, 0.6)
