from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map

MIN_ZOOM = 1.5
INITIAL_ZOOM = 1.5
MAX_ZOOM = 20.0

WORLD_MIN_X, WORLD_MIN_Y = 0, 0
WORLD_MAX_X, WORLD_MAX_Y = 15393, 6566  # Example world


class Camera:
    def __init__(self, map: Map):
        self.map = map
        # Start centered in the world
        self.x = (WORLD_MIN_X + WORLD_MAX_X) / 2
        self.y = (WORLD_MIN_Y + WORLD_MAX_Y) / 2
        self.zoom = INITIAL_ZOOM

        # Camera movement bounds (None = no limit)
        self.min_x = WORLD_MIN_X
        self.min_y = WORLD_MIN_Y
        self.max_x = WORLD_MAX_X
        self.max_y = WORLD_MAX_Y

    def _get_visible_rect(self):
        """Calculate the visible world space dimensions based on zoom and aspect ratio."""
        screen_width = self.map.width()
        screen_height = self.map.height()
        aspect_ratio = screen_width / screen_height

        world_width = (WORLD_MAX_X - WORLD_MIN_X) / self.zoom
        world_height = (WORLD_MAX_Y - WORLD_MIN_Y) / self.zoom

        if aspect_ratio > 1:
            world_width *= aspect_ratio
        else:
            world_height /= aspect_ratio

        left = self.x - world_width / 2
        right = self.x + world_width / 2
        bottom = self.y - world_height / 2
        top = self.y + world_height / 2
        return left, right, bottom, top

    def _clamp_position(self):
        """Clamp camera viewport to world. Such that one cannot see beyond world edges."""
        left, right, bottom, top = self._get_visible_rect()
        world_width = right - left
        world_height = top - bottom

        half_width = world_width / 2
        half_height = world_height / 2

        self.x = max(self.x, self.min_x + half_width)
        self.x = min(self.x, self.max_x - half_width)
        self.y = max(self.y, self.min_y + half_height)
        self.y = min(self.y, self.max_y - half_height)


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
        screen_x, screen_y = self.world_to_screen(self.x, self.y)
        screen_x += dx
        screen_y += dy
        self.x, self.y = self.screen_to_world(screen_x, screen_y)
        self._clamp_position()

    def zoom_to(self, new_zoom, mouse_x, mouse_y):
        """Zoom toward the mouse cursor, like Google Maps."""
        # World space under cursor before zoom
        if new_zoom < MIN_ZOOM or new_zoom > MAX_ZOOM:
            return

        before = self.screen_to_world(mouse_x, mouse_y)

        # Apply zoom
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

    def world_to_screen(self, wx, wy):
        """Convert world coordinates to screen coordinates."""
        width = self.map.width()
        height = self.map.height()

        # Apply view-projection
        vp = self.get_view_projection_matrix()
        sx, sy, _ = vp @ np.array([wx, wy, 1])

        # Convert NDC → screen
        sx = (sx + 1) / 2 * width
        sy = (1 - sy) / 2 * height

        return np.array([sx, sy], dtype=np.float32)

    def get_view_projection_matrix(self):
        """
        Returns the view-projection matrix that maps from world coordinates to NDC.
        """
        # Calculate the visible world space based on zoom and screen aspect ratio
        left, right, bottom, top = self._get_visible_rect()

        # Orthographic projection from world space to NDC
        proj = np.array([
            [2 / (right - left), 0, -(right + left) / (right - left)],
            [0, 2 / (bottom - top), -(bottom + top) / (bottom - top)],
            [0, 0, 1]
        ], dtype=np.float32)

        return proj