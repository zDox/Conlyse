"""Camera system for map navigation and viewport management."""

from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

from conlyse.logger import get_logger
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

logger = get_logger()
VERTICAL_SCALE = 0.4

class Camera:
    """
    Manages camera position, zoom, and viewport transformations for the map.

    The camera provides orthographic projection with zoom and pan capabilities,
    allowing users to navigate the game world. It handles coordinate transformations
    between screen space and world space, and ensures the viewport stays within
    world boundaries.

    The VERTICAL_SCALE compresses the vertical axis for a more cinematic aspect ratio.
    """

    def __init__(self, map_widget: Map):
        """
        Initialize the camera.

        Args:
            map_widget: The Map widget this camera is attached to
        """
        self.map = map_widget
        self.min_x = self.map.world_min_x
        self.max_x = self.map.world_max_x
        self.min_y = self.map.world_min_y
        self.max_y = self.map.world_max_y

        self.world_width = self.map.world_width
        self.world_height = self.map.world_height

        # Start centered in the world
        self.x: float = self.world_width / 2
        self.y: float = self.world_height / 2
        self.zoom: float = INITIAL_ZOOM

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

        world_height /= VERTICAL_SCALE

        left = self.x - world_width / 2
        right = self.x + world_width / 2
        bottom = self.y - world_height / 2
        top = self.y + world_height / 2

        return left, right, bottom, top

    def _clamp_position(self):
        """
        Clamp vertically, wrap horizontally.
        """
        left, right, bottom, top = self._get_visible_rect()
        world_height = top - bottom

        half_height = world_height / 2

        # ----- Horizontal wrapping -----
        total_width = self.max_x - self.min_x
        self.x = ((self.x - self.min_x) % total_width) + self.min_x

        # ----- Vertical clamping (no wrap) -----
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
        if new_zoom < MIN_ZOOM or new_zoom > MAX_ZOOM:
            return

        # World space under cursor before zoom
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

    def zoom_in(self):
        """Zoom in the camera by a fixed factor."""
        self.zoom_to(self.zoom * 1.1, self.map.width() / 2, self.map.height() / 2)

    def zoom_out(self):
        """Zoom out the camera by a fixed factor."""
        self.zoom_to(self.zoom * 0.9, self.map.width() / 2, self.map.height() / 2)

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

        The VERTICAL_SCALE is applied here to compress the vertical axis,
        creating a wider, more cinematic view.

        Returns:
            3x3 transformation matrix
        """
        left, right, bottom, top = self._get_visible_rect()

        # Standard orthographic projection with vertical scale applied
        proj = np.array([
            [2 / (right - left), 0, -(right + left) / (right - left)],
            [0, 2 / (bottom - top),
             -(bottom + top) / (bottom - top)],
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