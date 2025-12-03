from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map

MIN_ZOOM = 0.01
MAX_ZOOM = 20.0

WORLD_MIN_X, WORLD_MIN_Y = 0, 0
WORLD_MAX_X, WORLD_MAX_Y = 15393, 6566  # Example world


class Camera:
    def __init__(self, map: Map, x=0, y=0, zoom=1):
        self.map = map
        self.x = x  # Camera center in world coordinates
        self.y = y  # Camera center in world coordinates
        self.zoom = zoom

        # Camera movement bounds (None = no limit)
        self.min_x = None
        self.min_y = None
        self.max_x = None
        self.max_y = None

    def _clamp_position(self):
        """Clamp camera position to movement bounds."""
        if self.min_x is not None and self.x < self.min_x:
            self.x = self.min_x
        if self.max_x is not None and self.x > self.max_x:
            self.x = self.max_x
        if self.min_y is not None and self.y < self.min_y:
            self.y = self.min_y
        if self.max_y is not None and self.y > self.max_y:
            self.y = self.max_y

    def set_bounds(self, min_x=None, min_y=None, max_x=None, max_y=None):
        """Set world coordinate bounds for camera movement."""
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        self._clamp_position()

    def move(self, dx, dy):
        """
        Pan the camera by (dx, dy) in screen coordinates.
        """
        dx = dx / self.zoom
        dy = dy / self.zoom
        self.x += dx
        self.y -= dy
        self._clamp_position()

    def zoom_to(self, new_zoom, mouse_x, mouse_y):
        """Zoom toward the mouse cursor, like Google Maps."""
        # World space under cursor before zoom
        if new_zoom < MIN_ZOOM or new_zoom > MAX_ZOOM:
            return

        before = self.screen_to_world(mouse_x, mouse_y)

        # Apply zoom
        old = self.zoom
        self.zoom = new_zoom

        # World space under cursor after zoom
        after = self.screen_to_world(mouse_x, mouse_y)

        # Adjust camera so both match
        diff = after - before
        self.x -= diff[0]
        self.y -= diff[1]
        self._clamp_position()

    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates."""
        width = self.map.width()
        height = self.map.height()

        # Convert screen → NDC
        x = (sx / width) * 2 - 1
        y = 1 - (sy / height) * 2

        # Apply inverse view-projection
        vp = self.get_view_projection_matrix()
        inv_vp = np.linalg.inv(vp)

        wx, wy, _ = inv_vp @ np.array([x, y, 1])
        return np.array([wx, wy], dtype=np.float32)

    def get_view_projection_matrix(self):
        """
        Returns the view-projection matrix that maps from world coordinates to NDC.
        """
        # Calculate the visible world space based on zoom and screen aspect ratio
        screen_width = self.map.width()
        screen_height = self.map.height()
        aspect_ratio = screen_width / screen_height

        # World space dimensions visible at current zoom
        world_width = (WORLD_MAX_X - WORLD_MIN_X) / self.zoom
        world_height = (WORLD_MAX_Y - WORLD_MIN_Y) / self.zoom

        # Adjust for aspect ratio to prevent distortion
        if aspect_ratio > 1:
            world_width *= aspect_ratio
        else:
            world_height /= aspect_ratio

        # Calculate visible bounds centered on camera position
        left = self.x - world_width / 2
        right = self.x + world_width / 2
        bottom = self.y - world_height / 2
        top = self.y + world_height / 2

        # Orthographic projection from world space to NDC
        proj = np.array([
            [2 / (right - left), 0, -(right + left) / (right - left)],
            [0, 2 / (bottom - top), -(bottom + top) / (bottom - top)],
            [0, 0, 1]
        ], dtype=np.float32)

        return proj