from __future__ import annotations
import logging
import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QSurfaceFormat, QWheelEvent
from PyQt6.QtWidgets import QVBoxLayout
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger

from conlyse.logger import get_logger, setup_logger
from conlyse.pages.map_page.constants import (
    OPENGL_VERSION_MAJOR,
    OPENGL_VERSION_MINOR,
    UPDATE_FRAME_INTERVAL_MS,
)
from conlyse.pages.map_page.input_controller import InputController
from conlyse.pages.map_page.map import Map
from conlyse.pages.page import Page
from conlyse.utils.enums import PageType

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
        self.input_controller: InputController | None = None
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
        self.map_widget = Map(self.ritf, self.app.config_manager.main, self)
        app.main_window.resize(old_size.width(), old_size.height())
        
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


        layout.addWidget(self.map_widget)
        self.setLayout(layout)

        # Set up performance metrics for this page
        self.app.performance_window.clear_metrics()
        self.app.performance_window.set_page("Map Page")
        self.app.performance_window.add_metric("Province Fill")
        self.app.performance_window.add_metric("Province Connections")
        
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

    def update(self) -> None:
        """Update method called by the page manager."""
        self.input_controller.update_camera_from_keyboard()
        self.map_widget.update()
        
        # Update performance window if visible
        if self.app.performance_window.isVisible():
            # Throttle performance metric updates to reduce CPU overhead
            self.perf_update_counter += 1
            if self.perf_update_counter >= self.perf_update_interval:
                metrics = self.map_widget.get_performance_metrics()
                self.app.performance_window.update_metric("Province Fill", metrics["province_fill"])
                self.app.performance_window.update_metric("Province Connections", metrics["province_connections"])
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

    def clean_up(self) -> None:
        """Clean up resources when the page is closed."""
        self.map_widget.deleteLater()