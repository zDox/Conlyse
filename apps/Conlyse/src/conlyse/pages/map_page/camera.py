"""
Camera for Map Navigation
==========================
Manages the view of the map with position and zoom, handling world-to-screen
and screen-to-world coordinate transformations.

Author: Copilot
Date: 2025-12-02
"""

from __future__ import annotations

import math
from typing import Tuple


# Configuration
# Predefined zoom levels for smooth navigation
ZOOM_STEPS = [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
# Scale factor for isometric/angled map projection (simulates viewing angle)
VERTICAL_ANGLE_SCALE = 0.8


class Camera:
    """Manages the view of the map with position and zoom."""

    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize the camera.

        Args:
            screen_width: Width of the viewport in pixels
            screen_height: Height of the viewport in pixels
        """
        self.x = 0.0
        self.y = 0.0

        self.world_width = 15000
        self.world_height = 6000

        self.scale_factor = 1.0
        self.zoom = 1.0
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.zoom_steps = [round(z / self.scale_factor, 2) for z in ZOOM_STEPS]

    def world_to_screen(self, point: Tuple[float, float]) -> Tuple[int, int]:
        """
        Converts world coordinates to screen coordinates.

        Args:
            point: World coordinates (x, y)

        Returns:
            Screen coordinates (sx, sy)
        """
        wx, wy = point[0], point[1]
        sx = (wx - self.x) * self.zoom * self.scale_factor + self.screen_width / 2
        sy = ((wy - self.y) * self.zoom * self.scale_factor + self.screen_height / 2) * VERTICAL_ANGLE_SCALE
        return int(sx), int(sy)

    def screen_to_world(self, point: Tuple[int, int]) -> Tuple[float, float]:
        """
        Converts screen coordinates to world coordinates.

        Args:
            point: Screen coordinates (sx, sy)

        Returns:
            World coordinates (wx, wy)
        """
        sx, sy = point[0], point[1]

        # Reverse the transformation for the x-coordinate
        wx = (sx - self.screen_width / 2) / (self.zoom * self.scale_factor) + self.x

        # Reverse the transformation for the y-coordinate
        wy = ((sy / VERTICAL_ANGLE_SCALE) - self.screen_height / 2) / (self.zoom * self.scale_factor) + self.y
        
        return wx, wy

    def pan(self, dx: float, dy: float):
        """
        Moves the camera by dx, dy in screen coordinates.

        Args:
            dx: Change in x (screen coordinates)
            dy: Change in y (screen coordinates)
        """
        # Convert screen deltas to world deltas and update position
        self.x = self.x + dx / (self.zoom * self.scale_factor)
        self.y = self.y + dy / (self.zoom * self.scale_factor)

        # Limit camera position to prevent scrolling out of the map
        self.x = max(0, min(self.x, self.world_width))
        self.y = max(0, min(self.y, self.world_height))

    def zoom_at(self, factor: float, screen_point: Tuple[int, int]):
        """
        Zooms towards a screen point, keeping it fixed on screen.

        Args:
            factor: Zoom factor (e.g., 2.0 for doubling zoom)
            screen_point: Screen coordinates to zoom towards
        """
        sx, sy = screen_point
        
        # Convert screen point to world coordinates at current zoom
        wx = (sx - self.screen_width / 2) / (self.zoom * self.scale_factor) + self.x
        wy = ((sy / VERTICAL_ANGLE_SCALE) - self.screen_height / 2) / (self.zoom * self.scale_factor) + self.y
        
        # Update zoom
        new_zoom = math.ceil(self.zoom * factor * 100) / 100
        
        # Adjust camera position to keep the world point under the screen point
        self.x = wx - (wx - self.x) / factor
        self.y = wy - (wy - self.y) / factor
        self.zoom = new_zoom

    def zoom_in(self, screen_point: Tuple[int, int]):
        """
        Zooms to the next zoom level.

        Args:
            screen_point: Screen coordinates to zoom towards
        """
        if self.zoom not in self.zoom_steps:
            # Find closest zoom step
            self.zoom = min(self.zoom_steps, key=lambda z: abs(z - self.zoom))
        
        zoom_index = self.zoom_steps.index(self.zoom)
        if zoom_index == len(self.zoom_steps) - 1:
            return
        
        self.zoom_at(self.zoom_steps[zoom_index + 1] / self.zoom, screen_point)

    def zoom_out(self, screen_point: Tuple[int, int]):
        """
        Zooms to the previous zoom level.

        Args:
            screen_point: Screen coordinates to zoom towards
        """
        if self.zoom not in self.zoom_steps:
            # Find closest zoom step
            self.zoom = min(self.zoom_steps, key=lambda z: abs(z - self.zoom))
        
        zoom_index = self.zoom_steps.index(self.zoom)
        if zoom_index == 0:
            return
        
        self.zoom_at(self.zoom_steps[zoom_index - 1] / self.zoom, screen_point)

    def fit_to_map(self, map_bounds: Tuple[float, float, float, float], screen_size: Tuple[int, int]):
        """
        Adjusts position and zoom to fit the entire map with a margin.

        Args:
            map_bounds: Map bounding box (min_x, min_y, max_x, max_y)
            screen_size: Screen dimensions (width, height)
        """
        self.screen_width, self.screen_height = screen_size
        min_x, min_y, max_x, max_y = map_bounds
        world_width = max_x - min_x
        world_height = max_y - min_y
        self.world_width = world_width
        self.world_height = world_height
        self.zoom = self.zoom_steps[1]
        self.x = (min_x + max_x) / 2
        self.y = (min_y + max_y) / 2

    def get_visible_rect(self) -> Tuple[float, float, float, float]:
        """
        Returns the visible rectangle in world coordinates.

        Returns:
            Tuple of (min_x, min_y, max_x, max_y)
        """
        # Get corners in world coordinates
        top_left = self.screen_to_world((0, 0))
        bottom_right = self.screen_to_world((self.screen_width, self.screen_height))
        
        return (top_left[0], top_left[1], bottom_right[0], bottom_right[1])

    def scale(self, x: float) -> float:
        """
        Scales a world-space distance to screen space.

        Args:
            x: Distance in world coordinates

        Returns:
            Distance in screen coordinates
        """
        return x * self.scale_factor * self.zoom
