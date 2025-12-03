from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map

MIN_ZOOM = 0.1
MAX_ZOOM = 10.0

class Camera:
    def __init__(self, map: Map, x=0, y=0, zoom=1):
        self.map = map
        self.x = x # Camera center in world coordinates
        self.y = y # Camera center in world coordinates
        self.zoom = zoom

    def move(self, dx, dy):
        """
        Pan the camera by (dx, dy) in screen coordinates.
        """
        dx = dx / self.zoom
        dy = dy / self.zoom
        self.x += dx
        self.y += dy


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
        print("Adjusting camera by", diff)
        self.x -= diff[0]
        self.y -= diff[1]

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
        left, right = 0, self.map.width()
        bottom, top = 0, self.map.height()

        # Orthographic projection
        proj = np.array([
            [2 / (right - left), 0, -(right + left) / (right - left)],
            [0, 2 / (top - bottom), -(top + bottom) / (top - bottom)],
            [0, 0, 1]
        ], dtype=np.float32)

        # View matrix (pan + zoom)
        view = np.array([
            [self.zoom, 0, -self.x * self.zoom],
            [0, self.zoom, -self.y * self.zoom],
            [0, 0, 1]
        ], dtype=np.float32)

        return proj @ view