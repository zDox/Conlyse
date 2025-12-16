from __future__ import annotations

import time
from typing import TYPE_CHECKING


from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QSurfaceFormat, QWheelEvent
from datetime import timedelta

from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QVBoxLayout, QWidget



from conlyse.logger import get_logger
from conlyse.pages.map_page.constants import (
    OPENGL_VERSION_MAJOR,
    OPENGL_VERSION_MINOR,

)
from conlyse.pages.map_page.input_controller import InputController
from conlyse.pages.map_page.map import Map
from conlyse.pages.page import Page
from conlyse.utils.enums import PageType
from conlyse.widgets.mui.button import CButton
from conlyse.widgets.timecontrol import TimelineControls

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()


class MapPage(Page):
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
        self.timeline_controls: TimelineControls | None = None
        self.timeline_button: CButton | None = None
        samples = self.app.config_manager.main.get("graphics.msaa_samples")

        # Configure OpenGL format BEFORE creating the Map widget
        fmt = QSurfaceFormat()
        fmt.setSamples(samples)
        fmt.setVersion(OPENGL_VERSION_MAJOR, OPENGL_VERSION_MINOR)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(fmt)

        # TODO: Fix resizing issue when creating the Map widget
        #
        old_size = app.main_window.size()
        print("Old size:", old_size.width(), old_size.height())
        self.map_widget = Map(self.ritf, self.app.config_manager.main, self)
        app.main_window.resize(old_size.width(), old_size.height())

        print(f"Map widget size after creation: {self.map_widget.width()}x{self.map_widget.height()}")
        # Performance tracking
        self.last_frame_time = time.perf_counter()
        self.frame_count = 0
        self.fps_update_interval = 0.5  # Update FPS every 0.5 seconds
        self.fps_timer = 0.0
        self.perf_update_counter = 0
        self.perf_update_interval = 10  # Update performance metrics every 10 frames

    def setup(self, context) -> None:
        """Initialize the UI layout and OpenGL context."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)


        if not self.ritf:
            logger.error(f"Replay not loaded for path: {self.app.replay_manager.active_replay_path}")
            self.app.page_manager.switch_to(PageType.ReplayListPage,
                                            error_message=f"Failed to load replay: {self.app.replay_manager.active_replay_path}")
            return

        self.ritf.register_province_trigger(["resource_production", "owner_id", "morale", "upgrade_set"])

        self.map_container = QWidget(self)
        container_layout = QVBoxLayout(self.map_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.map_widget)

        self.timeline_controls = TimelineControls(self.ritf, parent=self.map_container)
        self.timeline_controls.setVisible(False)
        self.timeline_controls.time_changed.connect(self._on_timeline_time_changed)

        layout.addWidget(self.map_container)
        self.setLayout(layout)

        self._setup_timeline_button()

        # Set up performance metrics for this page
        self.app.performance_window.clear_metrics()
        self.app.performance_window.set_page("Map Page")
        self.app.performance_window.add_metric("Last Jump Time")
        self.app.performance_window.add_metric("Province Fill")
        self.app.performance_window.add_metric("Province Connections")
        self.app.performance_window.add_metric("Province Borders")
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
                self.app.performance_window.update_metric("Last Jump Time", metrics["last_jump_time"])
                self.app.performance_window.update_metric("Province Fill", metrics["province_fill"])
                self.app.performance_window.update_metric("Province Connections", metrics["province_connections"])
                self.app.performance_window.update_metric("Province Borders", metrics["province_borders"])
                self.app.performance_window.update_metric("Terrain Map View Update", metrics["terrainview_update"])
                self.app.performance_window.update_metric("Resource Map View Update", metrics["resourceview_update"])
                self.app.performance_window.update_metric("Political Map View Update", metrics["politicalview_update"])
                self.app.performance_window.update_frame_time(metrics["total_frame"])
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


    def page_update(self, delta_time: float) -> None:
        """Update method called by the page manager."""
        self.input_controller.update_camera_from_keyboard()
        if self.timeline_controls:
            self.timeline_controls.advance_time(delta_time)
        self.map_widget.render_frame()

        self.update_performance_window()
        


    def clean_up(self) -> None:
        """Clean up resources when the page is closed."""
        self.input_controller.reset()
        self.map_widget.deleteLater()
        if self.timeline_controls:
            self.timeline_controls.clean_up()
            self.timeline_controls.deleteLater()
            self.timeline_controls = None
        if self.timeline_button:
            self.timeline_button.deleteLater()
            self.timeline_button = None
        self.app.main_window.header.set_actions([])

        self.ritf.unregister_province_trigger()

    def _setup_timeline_button(self) -> None:
        """Create and attach the header button that toggles the timeline panel."""
        self.timeline_button = CButton("Open Timeline", "contained", parent=self.app.main_window.header)
        self.timeline_button.clicked.connect(self.toggle_timeline_visibility)
        self.app.main_window.header.set_actions([self.timeline_button])

    def toggle_timeline_visibility(self) -> None:
        """Toggle visibility of the timeline controls panel."""
        if not self.timeline_controls:
            return
        is_visible = self.timeline_controls.isVisible()
        new_visible_state = not is_visible
        self.timeline_controls.setVisible(new_visible_state)
        if new_visible_state:
            self._position_timeline_overlay()
            self.timeline_controls.raise_()
        if self.timeline_button:
            self.timeline_button.setText("Close Timeline" if new_visible_state else "Open Timeline")

    def _on_timeline_time_changed(self, seconds: float) -> None:
        """Jump the replay interface to the requested timestamp."""
        if not self.ritf:
            return
        target_time = self.ritf.start_time + timedelta(seconds=seconds)
        t1 = time.perf_counter()
        self.ritf.jump_to(target_time)
        t2 = time.perf_counter()
        self.map_widget.performance_metrics["last_jump_time"] = t2 - t1
        hook_events = self.ritf.poll_events()

        self.map_widget.apply_hook_events(hook_events)

    def _position_timeline_overlay(self) -> None:
        """Position timeline overlay at the bottom of the map container."""
        if not self.timeline_controls or not self.map_container:
            return
        container_rect = self.rect()
        overlay_height = self.timeline_controls.sizeHint().height()
        self.timeline_controls.setGeometry(
            0,
            container_rect.height() - overlay_height,
            container_rect.width(),
            overlay_height,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_timeline_overlay()
