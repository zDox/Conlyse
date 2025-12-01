# conlyse/pages/replay_list_page.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QVBoxLayout

from conlyse.logger import get_logger
from conlyse.managers.keybinding_manager.key_action import KeyAction
from conlyse.pages.page import Page
from conlyse.pages.replay_list.replay_details_panel import ReplayDetailsPanel
from conlyse.pages.replay_list.replay_list_panel import ReplayListPanel
from conlyse.utils.enums import PageType

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()


class ReplayListPage(Page):
    """Page for displaying and managing replay files"""

    HEADER = False

    def __init__(self, app, parent=None):
        super().__init__(parent)

        self.app: App = app
        self.selected_replay = None
        self.selected_filepath: str | None = None

        # UI Components
        self.header_label = None
        self.subheader_label = None
        self.list_panel: ReplayListPanel | None = None
        self.details_panel: ReplayDetailsPanel | None = None

        # Track if UI has been set up
        self._ui_initialized = False
        # Track previous replay count for update detection
        self._previous_replay_count = 0

    def setup(self, context):
        """Called when page is opened - initialize UI"""
        if not self._ui_initialized:
            self.setup_ui()
            self._ui_initialized = True

        # Reset selection and refresh on page open
        self.selected_replay = None
        self.selected_filepath = self.app.replay_manager.active_replay_path
        self._previous_replay_count = len(self.app.replay_manager.get_replays())

        self.list_panel.refresh_list(self.app.replay_manager.get_replays())
        self._update_details()

        if context.get("error_message"):
            self._show_error_dialog(context["error_message"])

        self.app.keybinding_manager.register_action(
            KeyAction.OPEN_REPLAY_FILE_DIALOG,
            self.on_open_replay
        )

    def setup_ui(self):
        """One-time UI initialization"""
        self.setObjectName("replay_list_page")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)

        # Header section
        self._setup_header(main_layout)

        # Content area (list + details)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)

        # Left side - Replay list
        self.list_panel = ReplayListPanel()
        self.list_panel.set_callbacks(
            on_open=self.on_open_replay,
            on_selection_changed=self._on_replay_selected
        )
        content_layout.addWidget(self.list_panel)

        # Right side - Details
        self.details_panel = ReplayDetailsPanel()
        self.details_panel.set_callbacks(
            on_analyze=self._on_analyze_clicked,
            on_delete=self._on_delete_clicked
        )
        content_layout.addWidget(self.details_panel)

        main_layout.addLayout(content_layout)

    def _setup_header(self, parent_layout):
        """Setup the page header"""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        self.header_label = QLabel("Conflict of Nations Replay Analyser")
        self.header_label.setObjectName("replay_list_page_header")
        header_layout.addWidget(self.header_label)

        self.subheader_label = QLabel("View and analyze your recorded game replays")
        self.subheader_label.setObjectName("replay_list_page_subheader")
        header_layout.addWidget(self.subheader_label)

        parent_layout.addLayout(header_layout)

    def update(self):
        """Called every frame - check for changes and update if needed"""
        if not self._ui_initialized:
            return

        # Check if replay count has changed
        current_replay_count = len(self.app.replay_manager.get_replays())
        if current_replay_count != self._previous_replay_count:
            self._previous_replay_count = current_replay_count
            self.list_panel.refresh_list(self.app.replay_manager.get_replays())

    def _update_details(self):
        """Update the details panel with selected replay info"""
        self.details_panel.update_details(self.selected_replay, self.selected_filepath)

    def _on_replay_selected(self, replay):
        """Handle replay selection change"""
        self.selected_replay = replay
        self._update_details()

    def on_open_replay(self):
        """Handle opening a new replay file"""
        default_path = self.app.config_manager.get("file.default_open_path", "")
        replay_file_extension = self.app.config_manager.get("file.replay_file_extension", ".db")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Replay Database",
            default_path,
            f"Replay Files (*{replay_file_extension});;All Files (*.*)"
        )

        if not file_path:
            return

        logger.debug(f"Selected replay file: {file_path}")
        success = self.app.replay_manager.add_replay(file_path)

        if success:
            self._previous_replay_count = len(self.app.replay_manager.get_replays())
            self.selected_replay = self.app.replay_manager.get_replays()[file_path]
            self.selected_filepath = file_path
            self.app.config_manager.set("file.default_open_path", file_path)
            self.list_panel.refresh_list(self.app.replay_manager.get_replays())
            self._update_details()
        else:
            self._show_error_dialog(
                "Failed to open the selected replay file.",
                "The file may be corrupted or invalid."
            )

    def _on_analyze_clicked(self):
        """Handle analyze replay button click"""
        if not self.selected_filepath:
            return

        self.app.page_manager.switch_to(
            PageType.ReplayLoadPage,
            next_page=PageType.PlayerListPage,
            replay_path=self.selected_filepath
        )

    def _on_delete_clicked(self):
        """Handle delete replay button click"""
        if not self.selected_replay:
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Delete Replay",
            "Are you sure you want to delete this replay?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.app.replay_manager.remove_replay(self.selected_filepath)
            self._previous_replay_count = len(self.app.replay_manager.get_replays())
            self.selected_replay = None
            self.selected_filepath = None
            self.list_panel.refresh_list(self.app.replay_manager.get_replays())
            self._update_details()

    def _show_error_dialog(self, text, informative_text=None):
        """Show an error dialog"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText(text)
        if informative_text:
            msg.setInformativeText(informative_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def clean_up(self):
        """Called when page is closed - cleanup resources"""
        logger.debug("ReplayListPage cleanup")

        # Cleanup panels
        if self.list_panel:
            self.list_panel.cleanup()

        # Clear references
        self.selected_replay = None
        self.selected_filepath = None

        self.app.keybinding_manager.unregister_action(KeyAction.OPEN_REPLAY_FILE_DIALOG)