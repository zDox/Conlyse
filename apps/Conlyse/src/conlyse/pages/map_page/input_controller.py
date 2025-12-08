"""Input controller for handling user interactions with the map."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from conflict_interface.data_types.point import Point

from conlyse.pages.map_page.constants import CAMERA_MOVEMENT_STEP
from conlyse.pages.map_page.constants import KEYBOARD_MOVEMENT_CONFIG
from conlyse.pages.map_page.constants import ZOOM_FACTOR_IN
from conlyse.pages.map_page.constants import ZOOM_FACTOR_OUT

if TYPE_CHECKING:
    from conlyse.pages.map_page.map import Map


class InputController:
    """
    Handles keyboard and mouse input for map navigation.

    This class separates input handling logic from the main MapPage class.
    """

    def __init__(self, map_widget: Map):
        """
        Initialize the input controller.

        Args:
            map_widget: The Map widget to control
        """
        self.map_widget = map_widget
        self.last_mouse_pos: Point | None = None
        self.dragging = False
        self.pressed_keys: set[int] = set()

    def handle_key_press(self, event: QKeyEvent) -> None:
        """
        Handle key press events.

        Args:
            event: The key press event
        """
        self.pressed_keys.add(event.key())

    def handle_key_release(self, event: QKeyEvent) -> None:
        """
        Handle key release events.

        Args:
            event: The key release event
        """
        self.pressed_keys.discard(event.key())

    def handle_mouse_press(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events to start dragging.

        Args:
            event: The mouse press event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = Point(event.pos().x(), event.pos().y())
            self.dragging = True

    def handle_mouse_move(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events to pan the camera.

        Args:
            event: The mouse move event
        """
        if not self.dragging:
            return

        event_pos = Point(event.pos().x(), event.pos().y())
        delta = event_pos - self.last_mouse_pos
        self.last_mouse_pos = event_pos

        self.map_widget.handle_camera_move(-delta.x, -delta.y)

    def handle_mouse_release(self, event: QMouseEvent) -> None:
        """
        Handle mouse release events to stop dragging.

        Args:
            event: The mouse release event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def handle_wheel(self, event: QWheelEvent) -> None:
        """
        Handle mouse wheel events for zooming.

        Args:
            event: The wheel event
        """
        delta = event.angleDelta().y()
        zoom_factor = ZOOM_FACTOR_IN if delta > 0 else ZOOM_FACTOR_OUT
        new_zoom = self.map_widget.camera.zoom * zoom_factor
        x, y = event.position().x(), event.position().y()
        self.map_widget.camera.zoom_to(new_zoom, x, y)
        self.map_widget.update()

    def update_camera_from_keyboard(self) -> None:
        """
        Update camera position based on currently pressed keys.

        This should be called regularly (e.g., in a timer callback)
        to provide smooth continuous movement.
        """
        dx_total = 0
        dy_total = 0

        for key, (dx_norm, dy_norm) in KEYBOARD_MOVEMENT_CONFIG.items():
            if key in self.pressed_keys:
                dx_total += dx_norm * CAMERA_MOVEMENT_STEP
                dy_total += dy_norm * CAMERA_MOVEMENT_STEP

        if dx_total != 0 or dy_total != 0:
            self.map_widget.handle_camera_move(dx_total, dy_total)

    def reset(self) -> None:
        """Reset the input controller state."""
        self.last_mouse_pos = None
        self.dragging = False
        self.pressed_keys.clear()