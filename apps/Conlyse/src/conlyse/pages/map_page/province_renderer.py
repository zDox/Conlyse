"""
Province Renderer
=================
Renders provinces on the map using OpenGL with cached geometry.

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

from OpenGL.GL import GL_BLEND
from OpenGL.GL import GL_LINE_LOOP
from OpenGL.GL import GL_ONE_MINUS_SRC_ALPHA
from OpenGL.GL import GL_POLYGON
from OpenGL.GL import GL_SRC_ALPHA
from OpenGL.GL import glBegin
from OpenGL.GL import glBlendFunc
from OpenGL.GL import glColor4f
from OpenGL.GL import glEnable
from OpenGL.GL import glEnd
from OpenGL.GL import glLineWidth
from OpenGL.GL import glVertex2f

from conlyse.logger import get_logger
from conlyse.pages.map_page.entity_renderer import EntityRenderer

if TYPE_CHECKING:
    from conlyse.pages.map_page.camera import Camera

logger = get_logger()


class ProvinceData:
    """Stores cached data for a single province."""
    
    def __init__(self, province_id: int):
        self.province_id = province_id
        self.bounds = (0.0, 0.0, 0.0, 0.0)  # min_x, max_x, min_y, max_y (world space)
        self.world_coords = []  # World coordinates cached in memory
        self.color = (0.8, 0.8, 0.8, 0.4)  # RGBA color
        

class ProvinceRenderer(EntityRenderer):
    """
    Renders provinces with their borders and colors.
    
    This renderer caches province geometry in memory and only updates when
    province data changes, avoiding expensive per-frame data processing.
    """

    def __init__(self):
        """Initialize the province renderer."""
        super().__init__()
        self.province_data: Dict[int, ProvinceData] = {}
        self.dirty_provinces: Set[int] = set()
        self._needs_full_rebuild = False

    def initialize(self):
        """Initialize OpenGL resources for province rendering."""
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._initialized = True
        logger.info("Province renderer initialized")

    def set_province_color(self, province_id: int, color: Tuple[float, float, float, float]):
        """
        Set the color for a specific province and mark it as dirty.

        Args:
            province_id: Province ID
            color: RGBA color (values 0-1)
        """
        if province_id in self.province_data:
            old_color = self.province_data[province_id].color
            if old_color != color:
                self.province_data[province_id].color = color
        self.dirty_provinces.add(province_id)

    def mark_province_dirty(self, province_id: int):
        """
        Mark a province as dirty, requiring geometry rebuild.
        
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

    def _build_province_data(self, province_id: int, province: Any, color: Tuple[float, float, float, float]):
        """
        Build cached data for a single province.
        
        Stores world coordinates in memory to avoid reprocessing province geometry.

        Args:
            province_id: Province ID
            province: Province object with static_data.borders
            color: RGBA color for the province
        """
        if not hasattr(province, 'static_data') or not hasattr(province.static_data, 'borders'):
            return

        # Get world coordinates
        world_coords = [(point.x, point.y) for point in province.static_data.borders]
        if not world_coords:
            return

        # Calculate bounds in world space
        bounds = self._calculate_bounds(world_coords)

        # Get or create province data
        if province_id not in self.province_data:
            self.province_data[province_id] = ProvinceData(province_id)
        
        pdata = self.province_data[province_id]
        pdata.bounds = bounds
        pdata.world_coords = world_coords
        pdata.color = color

    def _rebuild_dirty_provinces(self, provinces: Dict[int, Any], province_colors: Dict[int, Tuple[float, float, float, float]]):
        """
        Rebuild cached data for provinces that have changed.

        Args:
            provinces: Dictionary of province_id -> province object
            province_colors: Dictionary of province_id -> color
        """
        if not self.dirty_provinces:
            return

        for province_id in list(self.dirty_provinces):
            if province_id in provinces:
                color = province_colors.get(province_id, (0.8, 0.8, 0.8, 0.4))
                self._build_province_data(province_id, provinces[province_id], color)
        
        self.dirty_provinces.clear()
        logger.debug(f"Rebuilt data for dirty provinces")

    def _build_all_data(self, provinces: Dict[int, Any], province_colors: Dict[int, Tuple[float, float, float, float]]):
        """
        Build cached data for all provinces (initial load or full rebuild).

        Args:
            provinces: Dictionary of province_id -> province object
            province_colors: Dictionary of province_id -> color
        """
        logger.info(f"Building cached data for {len(provinces)} provinces")
        for province_id, province in provinces.items():
            color = province_colors.get(province_id, (0.8, 0.8, 0.8, 0.4))
            self._build_province_data(province_id, province, color)
        self._needs_full_rebuild = False
        logger.info("Province data caching complete")

    def update_provinces(self, provinces: Dict[int, Any], province_colors: Dict[int, Tuple[float, float, float, float]]):
        """
        Update province data - call this when provinces are first loaded or change.

        Args:
            provinces: Dictionary of province_id -> province object
            province_colors: Dictionary of province_id -> color
        """
        if self._needs_full_rebuild or not self.province_data:
            self._build_all_data(provinces, province_colors)
        else:
            self._rebuild_dirty_provinces(provinces, province_colors)

    def render(self, camera: Camera, provinces: Dict[int, Any]):
        """
        Render provinces using cached geometry data.
        
        World coordinates are cached in memory and transformed to screen space
        during rendering. Only provinces are reprocessed when they change.

        Args:
            camera: Camera for coordinate transformations
            provinces: Dictionary of province_id -> province object (only needed for initial load)
        """
        if not self._initialized:
            return

        visible_rect = camera.get_visible_rect()

        # Render province fills
        for province_id, pdata in self.province_data.items():
            # Frustum culling in world space
            min_x, max_x, min_y, max_y = pdata.bounds
            if (max_x < visible_rect[0] or min_x > visible_rect[2] or
                max_y < visible_rect[1] or min_y > visible_rect[3]):
                continue

            if not pdata.world_coords:
                continue

            # Transform world coordinates to screen coordinates for rendering
            screen_coords = [camera.world_to_screen(p) for p in pdata.world_coords]
            
            # Render filled polygon
            glColor4f(*pdata.color)
            glBegin(GL_POLYGON)
            for sx, sy in screen_coords:
                glVertex2f(sx, sy)
            glEnd()

        # Render province borders
        glColor4f(0.0, 0.0, 0.0, 1.0)  # Black borders
        glLineWidth(1.0)

        for province_id, pdata in self.province_data.items():
            # Frustum culling in world space
            min_x, max_x, min_y, max_y = pdata.bounds
            if (max_x < visible_rect[0] or min_x > visible_rect[2] or
                max_y < visible_rect[1] or min_y > visible_rect[3]):
                continue

            if not pdata.world_coords:
                continue

            # Transform world coordinates to screen coordinates
            screen_coords = [camera.world_to_screen(p) for p in pdata.world_coords]
            
            # Render border
            glBegin(GL_LINE_LOOP)
            for sx, sy in screen_coords:
                glVertex2f(sx, sy)
            glEnd()

    def cleanup(self):
        """Clean up resources."""
        self.province_data.clear()
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
