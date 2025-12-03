from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map


class Camera:
    def __init__(self, map: Map, x=0, y=0, zoom=1):
        self.map = map
        self.x = x
        self.y = y
        self.zoom = zoom

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def set_zoom(self, zoom):
        self.zoom = zoom


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