from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from conlyse.logger import get_logger
from conlyse.pages.map_page.constants import OPENGL_VERSION_MAJOR
from conlyse.pages.map_page.constants import OPENGL_VERSION_MINOR
from conlyse.pages.map_page.input_controller import InputController
from conlyse.pages.map_page.map import Map
from conlyse.pages.replay_page import ReplayPage

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()


class MapPage(ReplayPage):
    """
    Page for displaying and interacting with the game map.
    """

    def __init__(self, app: App, parent=None):
        """
        Initialize the MapPage.

        Args:
            app: The main application instance

        The replay interface (`ritf`) is obtained from `self.app.replay_manager.get_active_replay()`.
        """
        super().__init__(app, parent)
        self.app: App = app
        self.ritf = self.app.replay_manager.get_active_replay()
        self.map_widget: Map | None = None
        self.map_container: QWidget | None = None
        self.input_controller: InputController | None = None
        samples = self.app.config_manager.main.get("graphics.msaa_samples")

        # Configure OpenGL format BEFORE creating the Map widget
        fmt = QSurfaceFormat()
        fmt.setSamples(samples)
        if self.app.config_manager.main.get("graphics.vsync"):
            fmt.setSwapInterval(1)
        else:
            fmt.setSwapInterval(0)
        fmt.setVersion(OPENGL_VERSION_MAJOR, OPENGL_VERSION_MINOR)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(fmt)

        # TODO: Fix resizing issue when creating the Map widget
        old_size = app.main_window.size()
        self.map_widget = Map(self.ritf, self.app.config_manager.main, self)
        app.main_window.resize(old_size.width(), old_size.height())

        # Performance tracking
        self.last_frame_time = time.perf_counter()
        self.frame_count = 0
        self.fps_update_interval = 0.5  # Update FPS every 0.5 seconds
        self.fps_timer = 0.0
        self.perf_update_counter = 0
        self.perf_update_interval = 100  # Update performance metrics every 100 frames

    def setup(self, context) -> None:
        """Initialize the UI layout and OpenGL context."""
        super().setup(context)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.ritf.register_province_trigger(["resource_production", "owner_id", "morale", "upgrade_set"])

        self.map_container = QWidget(self)
        container_layout = QVBoxLayout(self.map_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.map_widget)


        layout.addWidget(self.map_container)
        self.setLayout(layout)


        # Set up performance metrics for this page
        self.app.performance_window.clear_metrics()
        self.app.performance_window.set_page("Map Page")
        self.app.performance_window.add_metric("Render Frame")
        self.app.performance_window.add_metric("Time Since Last Frame")
        self.app.performance_window.add_metric("Last Jump Time")
        self.app.performance_window.add_metric("Province Fill")
        self.app.performance_window.add_metric("Province Connections")
        self.app.performance_window.add_metric("Province Borders")
        self.app.performance_window.add_metric("World Text")
        self.app.performance_window.add_metric("Terrain Map View Update")
        self.app.performance_window.add_metric("Resource Map View Update")
        self.app.performance_window.add_metric("Political Map View Update")
        self.input_controller = InputController(self.map_widget, self.app.keybinding_manager)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)

    # ---- Input event handlers ----
    # These methods forward events to the InputController

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.input_controller.handle_key_press(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.input_controller.handle_key_release(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.input_controller.handle_mouse_press(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.input_controller.handle_mouse_move(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.input_controller.handle_mouse_release(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.input_controller.handle_wheel(event)

    def update_performance_window(self) -> None:
        # Update performance window if visible
        if self.app.performance_window.isVisible():
            # Throttle performance metric updates to reduce CPU overhead
            self.perf_update_counter += 1
            if self.perf_update_counter >= self.perf_update_interval:
                metrics = self.map_widget.get_performance_metrics()
                self.app.performance_window.update_metric("Province Fill", metrics["province_fill"])
                self.app.performance_window.update_metric("Province Connections", metrics["province_connections"])
                self.app.performance_window.update_metric("Province Borders", metrics["province_borders"])
                self.app.performance_window.update_metric("World Text", metrics["world_text"])
                self.app.performance_window.update_metric("Terrain Map View Update", metrics["terrainview_update"])
                self.app.performance_window.update_metric("Resource Map View Update", metrics["resourceview_update"])
                self.app.performance_window.update_metric("Political Map View Update", metrics["politicalview_update"])
                self.app.performance_window.update_metric("Render Frame", metrics["render_frame"])
                self.app.performance_window.update_metric("Time Since Last Frame", metrics["time_since_last_frame"])
                self.perf_update_counter = 0

            # Calculate FPS
            current_time = time.perf_counter()
            self.frame_count += 1
            self.fps_timer += current_time - self.last_frame_time
            self.last_frame_time = current_time

            if self.fps_timer >= self.fps_update_interval:
                fps = self.frame_count / self.fps_timer
                self.app.performance_window.update_fps(fps)
                self.frame_count = 0
                self.fps_timer = 0.0

    def page_update(self, dt: float) -> None:
        """Update method called by the page manager."""
        super().page_update(dt)
        self.input_controller.update_camera_from_keyboard()

    def page_render(self, dt: float) -> None:
        """Render method called by the page manager."""
        super().page_render(dt)
        if self.map_widget:
            self.map_widget.render_frame()
        self.update_performance_window()

    def clean_up(self) -> None:
        """Clean up resources when the page is closed."""
        super().clean_up()
        self.input_controller.reset()
        if self.map_widget:
            self.map_widget.cleanup()
        self.map_widget.deleteLater()
        self.app.main_window.header.set_actions([])

        self.ritf.unregister_province_trigger()

    def _on_replay_jump(self) -> None:
        """Jump the replay interface to the requested timestamp."""
        hook_events = self.ritf.poll_events()

        self.map_widget.apply_hook_events(hook_events)