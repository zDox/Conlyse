"""Camera system for map navigation and viewport management."""

from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL as gl

from conlyse.pages.map_page.constants import INITIAL_ZOOM
from conlyse.pages.map_page.constants import MAX_ZOOM
from conlyse.pages.map_page.constants import MIN_ZOOM
from conlyse.pages.map_page.constants import WORLD_MAX_X
from conlyse.pages.map_page.constants import WORLD_MAX_Y
from conlyse.pages.map_page.constants import WORLD_MIN_X
from conlyse.pages.map_page.constants import WORLD_MIN_Y
from conlyse.pages.map_page.opengl_wrapper.shader_program import ShaderProgram

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map


class Camera:
    """
    Manages camera position, zoom, and viewport transformations for the map.

    The camera provides orthographic projection with zoom and pan capabilities,
    allowing users to navigate the game world. It handles coordinate transformations
    between screen space and world space, and ensures the viewport stays within
    world boundaries.
    """

    def __init__(self, map_widget: Map):
        """
        Initialize the camera.

        Args:
            map_widget: The Map widget this camera is attached to
        """
        self.map = map_widget
        # Start centered in the world
        self.x: float = (WORLD_MIN_X + WORLD_MAX_X) / 2
        self.y: float = (WORLD_MIN_Y + WORLD_MAX_Y) / 2
        self.zoom: float = INITIAL_ZOOM

        # Camera movement bounds
        self.min_x: float = WORLD_MIN_X
        self.min_y: float = WORLD_MIN_Y
        self.max_x: float = WORLD_MAX_X
        self.max_y: float = WORLD_MAX_Y

    def _get_visible_rect(self) -> tuple[float, float, float, float]:
        """
        Calculate the visible world space dimensions based on zoom and aspect ratio.

        Returns:
            Tuple of (left, right, bottom, top) world coordinates
        """
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

    def _clamp_position(self) -> None:
        """
        Clamp camera viewport to world boundaries.

        Ensures that the camera cannot pan beyond the world edges,
        preventing the user from seeing outside the valid game area.
        """
        left, right, bottom, top = self._get_visible_rect()
        world_width = right - left
        world_height = top - bottom

        half_width = world_width / 2
        half_height = world_height / 2

        self.x = max(self.x, self.min_x + half_width)
        self.x = min(self.x, self.max_x - half_width)
        self.y = max(self.y, self.min_y + half_height)
        self.y = min(self.y, self.max_y - half_height)

    def move(self, dx: float, dy: float) -> None:
        """
        Pan the camera by (dx, dy) in screen coordinates.

        Args:
            dx: Horizontal movement in screen pixels
            dy: Vertical movement in screen pixels
        """
        screen_x, screen_y = self.world_to_screen(self.x, self.y)
        screen_x += dx
        screen_y += dy
        self.x, self.y = self.screen_to_world(screen_x, screen_y)
        self._clamp_position()

    def zoom_to(self, new_zoom: float, mouse_x: float, mouse_y: float) -> None:
        """
        Zoom toward the mouse cursor position.

        This provides a Google Maps-like zoom experience where the point
        under the cursor remains stationary during the zoom operation.

        Args:
            new_zoom: The target zoom level
            mouse_x: Mouse X position in screen coordinates
            mouse_y: Mouse Y position in screen coordinates
        """
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

    def screen_to_world(self, sx: float, sy: float) -> np.ndarray:
        """
        Convert screen coordinates to world coordinates.

        Args:
            sx: Screen X coordinate
            sy: Screen Y coordinate

        Returns:
            Array of [world_x, world_y] coordinates
        """
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

    def world_to_screen(self, wx: float, wy: float) -> np.ndarray:
        """
        Convert world coordinates to screen coordinates.

        Args:
            wx: World X coordinate
            wy: World Y coordinate

        Returns:
            Array of [screen_x, screen_y] coordinates
        """
        width = self.map.width()
        height = self.map.height()

        # Apply view-projection
        vp = self.get_view_projection_matrix()
        sx, sy, _ = vp @ np.array([wx, wy, 1])

        # Convert NDC → screen
        sx = (sx + 1) / 2 * width
        sy = (1 - sy) / 2 * height

        return np.array([sx, sy], dtype=np.float32)

    def get_view_projection_matrix(self) -> np.ndarray:
        """
        Calculate the view-projection matrix for rendering.

        Returns the combined view-projection matrix that transforms world
        coordinates to normalized device coordinates (NDC) for OpenGL rendering.

        Returns:
            3x3 transformation matrix
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

    def set_uniforms(self, program: ShaderProgram) -> None:
        """
        Set camera-related uniforms in the shader program.

        Args:
            program: The shader program to set uniforms for
        """
        program.set_uniform_matrix3fv(
            "uViewProjection", self.get_view_projection_matrix().T
        )