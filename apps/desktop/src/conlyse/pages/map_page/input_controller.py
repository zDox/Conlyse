"""Input controller for handling user interactions with the map."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtGui import QWheelEvent
from conflict_interface.data_types.newest.point import Point

from conlyse.logger import get_logger
from conlyse.managers.keybinding_manager.key_action import KeyAction
from conlyse.managers.keybinding_manager.keybinding_manager import KeybindingManager
from conlyse.pages.map_page.constants import CAMERA_MOVEMENT_STEP
from conlyse.pages.map_page.constants import ZOOM_FACTOR_IN
from conlyse.pages.map_page.constants import ZOOM_FACTOR_OUT
from conlyse.pages.map_page.map_views.map_view_type import MapViewType
from conlyse.utils.enums import DockType
from conlyse.widgets.dock_system.docks.province_info_dock import ProvinceInfoDock

if TYPE_CHECKING:
    from conlyse.pages.map_page.map_page import MapPage

logger = get_logger()

class InputController:
    """
    Handles keyboard and mouse input for map navigation.

    This class separates input handling logic from the main MapPage class.
    """

    def __init__(self, map_page: MapPage):
        """
        Initialize the input controller.

        Args:
            map_page: The Map Page to control
        """
        self.map_page = map_page
        self.map_widget = map_page.map_widget
        self.keybindings_manager = map_page.app.keybinding_manager
        self.last_mouse_pos: Point | None = None
        self.dragging = False
        self.moved_since_last_click = False
        self.pressed_keys: set[int] = set()
        self.enable_mouse_click_logging = False

        self.setup_keybindings()

    def setup_keybindings(self):
        self.keybindings_manager.register_action(
            KeyAction.CAMERA_ZOOM_IN, self.map_widget.camera.zoom_in
        )
        self.keybindings_manager.register_action(
            KeyAction.CAMERA_ZOOM_OUT, self.map_widget.camera.zoom_out
        )

        self.keybindings_manager.register_action(
            KeyAction.SWITCH_TO_POLITICAL_MAP_VIEW,
            lambda: self.map_widget.set_active_map_view(MapViewType.POLITICAL)
        )
        self.keybindings_manager.register_action(
            KeyAction.SWITCH_TO_TERRAIN_MAP_VIEW,
            lambda: self.map_widget.set_active_map_view(MapViewType.TERRAIN)
        )

        self.keybindings_manager.register_action(
            KeyAction.SWITCH_TO_RESOURCE_MAP_VIEW,
            lambda: self.map_widget.set_active_map_view(MapViewType.RESOURCE)
        )

        self.keybindings_manager.register_action(
            KeyAction.TOGGLE_CONNECTIONS_OVERLAY,
            self.map_widget.toggle_render_connections
        )

        self.keybindings_manager.register_action(
            KeyAction.DEBUG_TOGGLE_MOUSE_CLICK_LOGGING,
            self.toggle_mouse_click_logging
        )

    def toggle_mouse_click_logging(self) -> None:
        """Toggle logging of mouse click positions."""
        self.enable_mouse_click_logging = not self.enable_mouse_click_logging
        logger.info(f"Mouse click logging {'enabled' if self.enable_mouse_click_logging else 'disabled'}.")

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
            self.moved_since_last_click = False


            if self.enable_mouse_click_logging:
                world_pos = self.map_widget.camera.screen_to_world(event.pos().x(), event.pos().y())
                province_id = self.map_widget.get_province_id_at_world_position(world_pos[0], world_pos[1])
                province = self.map_widget.ritf.get_province(province_id) if province_id is not None else None
                province_name = province.name if province is not None else "Unknown"
                logger.debug(f"Mouse click at screen ({event.pos().x()}, {event.pos().y()}) "
                             f"-> world ({world_pos[0]:.2f}, {world_pos[1]:.2f}) Province ({province_name})")

    def handle_mouse_move(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events to pan the camera.

        Args:
            event: The mouse move event
        """
        if not self.dragging:
            return
        self.moved_since_last_click = True

        event_pos = Point(event.pos().x(), event.pos().y())
        delta = event_pos - self.last_mouse_pos
        self.last_mouse_pos = event_pos

        self.map_widget.camera.move(-delta.x, -delta.y)

    def handle_mouse_release(self, event: QMouseEvent) -> None:
        """
        Handle mouse release events to stop dragging.

        Args:
            event: The mouse release event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

            if not self.moved_since_last_click:
                world_pos = self.map_widget.camera.screen_to_world(event.pos().x(), event.pos().y())
                province_id = self.map_widget.get_province_id_at_world_position(world_pos[0], world_pos[1])

                province_info_dock: ProvinceInfoDock = cast(ProvinceInfoDock,
                                                            self.map_page.dock_system.get_dock(DockType.PROVINCE_INFO))
                province_info_dock.set_selected_province_id(province_id)

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

    def update_camera_from_keyboard(self) -> None:
        """
        Update camera position based on currently pressed keys.

        This should be called regularly (e.g., in a timer callback)
        to provide smooth continuous movement.
        """
        dx_total = 0
        dy_total = 0

        keyboard_movement_config = {
            self.keybindings_manager.get_key(KeyAction.CAMERA_MOVE_UP): (0, -1),
            self.keybindings_manager.get_key(KeyAction.CAMERA_MOVE_DOWN): (0, 1),
            self.keybindings_manager.get_key(KeyAction.CAMERA_MOVE_LEFT): (-1, 0),
            self.keybindings_manager.get_key(KeyAction.CAMERA_MOVE_RIGHT): (1, 0),
        }
        for key, (dx_norm, dy_norm) in keyboard_movement_config.items():
            if key is not None and key in self.pressed_keys:
                dx_total += dx_norm * CAMERA_MOVEMENT_STEP
                dy_total += dy_norm * CAMERA_MOVEMENT_STEP

        if dx_total != 0 or dy_total != 0:
            self.map_widget.camera.move(dx_total, dy_total)

    def reset(self) -> None:
        """Reset the input controller state."""
        self.last_mouse_pos = None
        self.dragging = False
        self.pressed_keys.clear()

        self.keybindings_manager.unregister_action(KeyAction.CAMERA_ZOOM_IN)
        self.keybindings_manager.unregister_action(KeyAction.CAMERA_ZOOM_OUT)
        self.keybindings_manager.unregister_action(KeyAction.SWITCH_TO_POLITICAL_MAP_VIEW)
        self.keybindings_manager.unregister_action(KeyAction.SWITCH_TO_TERRAIN_MAP_VIEW)
        self.keybindings_manager.unregister_action(KeyAction.SWITCH_TO_RESOURCE_MAP_VIEW)
        self.keybindings_manager.unregister_action(KeyAction.TOGGLE_CONNECTIONS_OVERLAY)
        self.keybindings_manager.unregister_action(KeyAction.DEBUG_TOGGLE_MOUSE_CLICK_LOGGING)
