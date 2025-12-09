from __future__ import annotations
import logging
from time import sleep
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QSurfaceFormat, QWheelEvent
from PyQt6.QtWidgets import QSizePolicy
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
            ritf: The replay interface providing game state data
        """
        super().__init__(app, parent)
        print(app.main_window.size())
        self.app: App = app
        self.ritf = self.app.replay_manager.get_active_replay()
        self.map_widget: Map | None = None
        self.input_controller: InputController | None = None
        # Configure OpenGL format BEFORE creating the Map widget
        fmt = QSurfaceFormat()
        fmt.setVersion(OPENGL_VERSION_MAJOR, OPENGL_VERSION_MINOR)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(fmt)

        # TODO: Fix resizing issue when creating the Map widget
        #
        old_size = app.main_window.size()
        self.map_widget = Map(self.ritf, self)
        app.main_window.resize(old_size.width(), old_size.height())

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

        self.input_controller = InputController(self.map_widget, self.app.keybinding_manager)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        print(self.app.main_window.size())


    def _on_frame_update(self) -> None:
        """Handle periodic frame updates for smooth keyboard input."""
        self.input_controller.update_camera_from_keyboard()

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

    def clean_up(self) -> None:
        """Clean up resources when the page is closed."""
        self.map_widget.deleteLater()


if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication

    setup_logger(logging.DEBUG)
    setup_library_logger(logging.DEBUG)
    app = QApplication([])

    ritf = ReplayInterface("test_replay.bin")
    ritf.open()
    logger.debug(f"Loaded replay: {ritf.replay.game_id}")

    static_province_ids = [
        p.id for p in ritf.game_state.states.map_state.map.static_map_data.locations
    ]
    province_ids = [p.id for p in ritf.get_provinces().values()]

    # Print differences in province IDs
    missing_in_static = set(province_ids) - set(static_province_ids)
    if missing_in_static:
        logger.warning(f"Provinces missing in static map data: {missing_in_static}")
    extra_in_static = set(static_province_ids) - set(province_ids)
    if extra_in_static:
        logger.warning(f"Extra provinces in static map data: {extra_in_static}")


    # Create a mock app object for standalone testing
    class MockApp:
        pass


    map_page = MapPage(MockApp(), ritf)
    map_page.setup({})
    map_page.resize(1200, 800)
    map_page.show()


    # Timer for smooth continuous key movement
    frame_timer = QTimer(map_page)
    frame_timer.timeout.connect(map_page._on_frame_update)
    frame_timer.start(UPDATE_FRAME_INTERVAL_MS)

    app.exec()