from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QVBoxLayout
from PyQt6.QtWidgets import QMessageBox

from conlyse.logger import get_logger
from conlyse.managers.events.event import Event
from conlyse.managers.events.replay_load_complete_event import ReplayOpenCompleteEvent
from conlyse.managers.events.replay_load_failed_event import ReplayOpenFailedEvent
from conlyse.pages.page import Page
from conlyse.utils.enums import PageType


if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()


class ReplayLoadPage(Page):
    """Loading page that displays an animated loading indicator"""

    HEADER = False

    def __init__(self, app, parent=None):
        super().__init__(parent)

        self.app: App = app
        self.loading_label = None
        self.animation_timer = None
        self.animation_state = 0

        # Loading animation frames
        self.loading_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        # Track if UI has been set up
        self._ui_initialized = False
        self.replay_path = None

        self.next_page_type = None

    def setup(self, context):
        """Called when page is opened - initialize UI and start animation"""
        self.replay_path = context.get("replay_path", None)
        self.next_page_type = context.get("next_page")

        if not self.replay_path or not self.app.replay_manager.is_valid_replay(self.replay_path):
            logger.error(f"Invalid replay path provided to ReplayLoadPage: {self.replay_path}")
            self.app.page_manager.switch_to(PageType.ReplayListPage, error_message="Invalid replay file selected.")
            return

        self.app.event_handler.subscribe(ReplayOpenCompleteEvent, self.on_replay_load_complete)
        self.app.event_handler.subscribe(ReplayOpenFailedEvent, self.on_replay_load_failed)
        self.app.replay_manager.open_replay_async(self.replay_path)

        if not self._ui_initialized:
            self.setup_ui()
            self._ui_initialized = True

        # Reset animation state
        self.animation_state = 0
        self.update_loading_icon()

        # Start animation timer
        if self.animation_timer:
            self.animation_timer.start(80)  # Update every 80ms for smooth animation

    def setup_ui(self):
        """One-time UI initialization"""
        # Main layout - center everything
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Loading icon label
        self.loading_label = QLabel(self.loading_frames[0])
        self.loading_label.setObjectName("loadingIcon")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(self.loading_label)

        # Setup animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate_loading)
        self.animation_timer.setInterval(80)  # 80ms per frame

    def update(self):
        """Called every frame - animation is handled by QTimer"""
        if not self._ui_initialized:
            return

        # Animation is handled by timer, nothing needed here
        pass

    def animate_loading(self):
        """Animate the loading icon"""
        self.animation_state = (self.animation_state + 1) % len(self.loading_frames)
        self.update_loading_icon()

    def update_loading_icon(self):
        """Update the loading icon to current animation frame"""
        if self.loading_label:
            self.loading_label.setText(self.loading_frames[self.animation_state])

    def on_replay_load_complete(self, event: Event):
        assert(isinstance(event, ReplayOpenCompleteEvent))

        if event.replay_file_path != self.replay_path:
            return

        self.app.page_manager.switch_to(self.next_page_type)

    def on_replay_load_failed(self, event: Event):
        assert(isinstance(event, ReplayOpenFailedEvent))

        if event.replay_file_path != self.replay_path:
            return

        logger.error(f"Failed to load replay: {event.trace_info}")
        self.app.page_manager.switch_to(PageType.ReplayListPage)

        # summon message box to inform user
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Replay Load Failed")
        msg_box.setText(f"Failed to load replay:\n{event.error_message}")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def clean_up(self):
        """Called when page is closed - stop animation"""
        # Stop the animation timer
        if self.animation_timer:
            self.animation_timer.stop()

        # Reset animation state
        self.animation_state = 0

        # Unsubscribe from events
        self.app.event_handler.unsubscribe(ReplayOpenCompleteEvent, self.on_replay_load_complete)
        self.app.event_handler.unsubscribe(ReplayOpenFailedEvent, self.on_replay_load_failed)

        # Labels get cleaned up by Qt parent-child system