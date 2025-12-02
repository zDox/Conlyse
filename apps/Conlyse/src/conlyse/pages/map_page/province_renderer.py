"""
Province Renderer
=================
Renders provinces on the map using OpenGL with GPU-accelerated VBOs.

Author: Copilot
Date: 2025-12-02
"""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Set
from typing import TYPE_CHECKING
from typing import Tuple

import numpy as np
from OpenGL.GL import GL_ARRAY_BUFFER
from OpenGL.GL import GL_BLEND
from OpenGL.GL import GL_COLOR_ARRAY
from OpenGL.GL import GL_DYNAMIC_DRAW
from OpenGL.GL import GL_FLOAT
from OpenGL.GL import GL_LINE_LOOP
from OpenGL.GL import GL_ONE_MINUS_SRC_ALPHA
from OpenGL.GL import GL_POLYGON
from OpenGL.GL import GL_SRC_ALPHA
from OpenGL.GL import GL_STATIC_DRAW
from OpenGL.GL import GL_VERTEX_ARRAY
from OpenGL.GL import glBindBuffer
from OpenGL.GL import glBlendFunc
from OpenGL.GL import glBufferData
from OpenGL.GL import glColor4f
from OpenGL.GL import glColorPointer
from OpenGL.GL import glDeleteBuffers
from OpenGL.GL import glDisableClientState
from OpenGL.GL import glDrawArrays
from OpenGL.GL import glEnable
from OpenGL.GL import glEnableClientState
from OpenGL.GL import glGenBuffers
from OpenGL.GL import glLineWidth
from OpenGL.GL import glVertexPointer

from conlyse.logger import get_logger
from conlyse.pages.map_page.entity_renderer import EntityRenderer

if TYPE_CHECKING:
    from conlyse.pages.map_page.camera import Camera

logger = get_logger()


class ProvinceData:
    """Stores GPU buffer data for a single province."""
    
    def __init__(self, province_id: int):
        self.province_id = province_id
        self.fill_vbo = None
        self.fill_color_vbo = None
        self.fill_vertex_count = 0
        self.border_vbo = None
        self.border_vertex_count = 0
        self.bounds = (0.0, 0.0, 0.0, 0.0)  # min_x, max_x, min_y, max_y
        self.world_coords = []  # Store for coordinate transformations
        

class ProvinceRenderer(EntityRenderer):
    """
    Renders provinces with their borders and colors using GPU-accelerated VBOs.
    
    This renderer stores province geometry on the GPU and only updates when
    province data changes, avoiding expensive per-frame loops.
    """

    def __init__(self):
        """Initialize the province renderer."""
        super().__init__()
        self.province_colors: Dict[int, Tuple[float, float, float, float]] = {}
        self.province_data: Dict[int, ProvinceData] = {}
        self.dirty_provinces: Set[int] = set()
        self._needs_full_rebuild = False

    def initialize(self):
        """Initialize OpenGL resources for province rendering."""
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._initialized = True
        logger.info("Province renderer initialized with VBO support")

    def set_province_color(self, province_id: int, color: Tuple[float, float, float, float]):
        """
        Set the color for a specific province and mark it as dirty.

        Args:
            province_id: Province ID
            color: RGBA color (values 0-1)
        """
        old_color = self.province_colors.get(province_id)
        if old_color != color:
            self.province_colors[province_id] = color
            self.dirty_provinces.add(province_id)

    def mark_province_dirty(self, province_id: int):
        """
        Mark a province as dirty, requiring VBO rebuild.
        
        This should be called when a province changes ownership or attributes.

        Args:
            province_id: Province ID that changed
        """
        self.dirty_provinces.add(province_id)
        logger.debug(f"Province {province_id} marked as dirty")

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

    def _build_province_vbos(self, province_id: int, province: Any, camera: Camera):
        """
        Build VBOs for a single province and store on GPU.

        Args:
            province_id: Province ID
            province: Province object with static_data.borders
            camera: Camera for coordinate transformations
        """
        if not hasattr(province, 'static_data') or not hasattr(province.static_data, 'borders'):
            return

        # Get world coordinates
        world_coords = [(point.x, point.y) for point in province.static_data.borders]
        if not world_coords:
            return

        # Calculate bounds
        bounds = self._calculate_bounds(world_coords)

        # Get or create province data
        if province_id not in self.province_data:
            self.province_data[province_id] = ProvinceData(province_id)
        
        pdata = self.province_data[province_id]
        pdata.bounds = bounds
        pdata.world_coords = world_coords

        # Convert to screen coordinates
        screen_coords = [camera.world_to_screen(p) for p in world_coords]
        
        # Create numpy arrays for vertices
        vertices = np.array(screen_coords, dtype=np.float32)
        
        # Get color for this province
        color = self.province_colors.get(province_id, (0.8, 0.8, 0.8, 0.4))
        colors = np.array([color] * len(screen_coords), dtype=np.float32)

        # Delete old VBOs if they exist
        if pdata.fill_vbo is not None:
            glDeleteBuffers(1, [pdata.fill_vbo])
        if pdata.fill_color_vbo is not None:
            glDeleteBuffers(1, [pdata.fill_color_vbo])
        if pdata.border_vbo is not None:
            glDeleteBuffers(1, [pdata.border_vbo])

        # Create VBO for fill vertices
        pdata.fill_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, pdata.fill_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        pdata.fill_vertex_count = len(vertices)

        # Create VBO for fill colors
        pdata.fill_color_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, pdata.fill_color_vbo)
        glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)

        # Create VBO for border (same vertices, just rendered differently)
        pdata.border_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, pdata.border_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        pdata.border_vertex_count = len(vertices)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _rebuild_dirty_provinces(self, provinces: Dict[int, Any], camera: Camera):
        """
        Rebuild VBOs for provinces that have changed.

        Args:
            provinces: Dictionary of province_id -> province object
            camera: Camera for coordinate transformations
        """
        if not self.dirty_provinces:
            return

        for province_id in list(self.dirty_provinces):
            if province_id in provinces:
                self._build_province_vbos(province_id, provinces[province_id], camera)
        
        self.dirty_provinces.clear()
        logger.debug(f"Rebuilt VBOs for dirty provinces")

    def _build_all_vbos(self, provinces: Dict[int, Any], camera: Camera):
        """
        Build VBOs for all provinces (initial load or full rebuild).

        Args:
            provinces: Dictionary of province_id -> province object
            camera: Camera for coordinate transformations
        """
        logger.info(f"Building VBOs for {len(provinces)} provinces")
        for province_id, province in provinces.items():
            self._build_province_vbos(province_id, province, camera)
        self._needs_full_rebuild = False
        logger.info("VBO build complete")

    def update_provinces(self, provinces: Dict[int, Any], camera: Camera):
        """
        Update province data - call this when provinces change or camera moves significantly.

        Args:
            provinces: Dictionary of province_id -> province object
            camera: Camera for coordinate transformations
        """
        if self._needs_full_rebuild or not self.province_data:
            self._build_all_vbos(provinces, camera)
        else:
            self._rebuild_dirty_provinces(provinces, camera)

    def render(self, camera: Camera, provinces: Dict[int, Any]):
        """
        Render provinces using GPU-stored VBOs.

        Args:
            camera: Camera for coordinate transformations
            provinces: Dictionary of province_id -> province object (only needed for updates)
        """
        if not self._initialized:
            return

        # Rebuild dirty provinces if needed
        if self.dirty_provinces or not self.province_data:
            self.update_provinces(provinces, camera)

        visible_rect = camera.get_visible_rect()

        # Enable vertex and color arrays
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        # Render province fills
        for province_id, pdata in self.province_data.items():
            # Frustum culling
            min_x, max_x, min_y, max_y = pdata.bounds
            if (max_x < visible_rect[0] or min_x > visible_rect[2] or
                max_y < visible_rect[1] or min_y > visible_rect[3]):
                continue

            if pdata.fill_vbo is None or pdata.fill_vertex_count == 0:
                continue

            # Bind vertex buffer
            glBindBuffer(GL_ARRAY_BUFFER, pdata.fill_vbo)
            glVertexPointer(2, GL_FLOAT, 0, None)

            # Bind color buffer
            glBindBuffer(GL_ARRAY_BUFFER, pdata.fill_color_vbo)
            glColorPointer(4, GL_FLOAT, 0, None)

            # Draw polygon
            glDrawArrays(GL_POLYGON, 0, pdata.fill_vertex_count)

        # Render province borders
        glColor4f(0.0, 0.0, 0.0, 1.0)  # Black borders
        glLineWidth(1.0)
        glDisableClientState(GL_COLOR_ARRAY)

        for province_id, pdata in self.province_data.items():
            # Frustum culling
            min_x, max_x, min_y, max_y = pdata.bounds
            if (max_x < visible_rect[0] or min_x > visible_rect[2] or
                max_y < visible_rect[1] or min_y > visible_rect[3]):
                continue

            if pdata.border_vbo is None or pdata.border_vertex_count == 0:
                continue

            # Bind vertex buffer
            glBindBuffer(GL_ARRAY_BUFFER, pdata.border_vbo)
            glVertexPointer(2, GL_FLOAT, 0, None)

            # Draw line loop
            glDrawArrays(GL_LINE_LOOP, 0, pdata.border_vertex_count)

        # Cleanup
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_VERTEX_ARRAY)

    def cleanup(self):
        """Clean up OpenGL resources."""
        # Delete all VBOs
        for pdata in self.province_data.values():
            if pdata.fill_vbo is not None:
                glDeleteBuffers(1, [pdata.fill_vbo])
            if pdata.fill_color_vbo is not None:
                glDeleteBuffers(1, [pdata.fill_color_vbo])
            if pdata.border_vbo is not None:
                glDeleteBuffers(1, [pdata.border_vbo])
        
        self.province_data.clear()
        self.province_colors.clear()
        self.dirty_provinces.clear()
        self._initialized = False
        logger.info("Province renderer cleaned up")


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
