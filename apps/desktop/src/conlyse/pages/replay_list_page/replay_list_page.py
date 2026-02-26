# conlyse/pages/replay_list_page.py

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QInputDialog

from conlyse.constants import START_REPLAY_PAGE
from conlyse.logger import get_logger
from conlyse.managers.keybinding_manager.key_action import KeyAction
from conlyse.pages.page import Page
from conlyse.pages.replay_list_page.replay_details_panel import ReplayDetailsPanel
from conlyse.pages.replay_list_page.replay_list_panel import ReplayListPanel
from conlyse.utils.enums import PageType
from conlyse.utils.downloads import download_to_file
from conlyse.widgets.mui.button import CButton
from conlyse.widgets.mui.icon_button import CIconButton

logger = get_logger()


class ReplayListPage(Page):
    """Page for displaying and managing replay files"""

    HEADER = False

    def __init__(self, app, parent=None):
        super().__init__(app, parent)

        self.selected_replay = None
        self.selected_filepath: str | None = None

        # UI Components
        self.header_label = None
        self.subheader_label = None
        self.list_panel: ReplayListPanel | None = None
        self.details_panel: ReplayDetailsPanel | None = None

        # Track previous replay count for update detection
        self._previous_replay_count = 0

    def setup(self, context):
        """Called when page is opened - initialize UI"""
        self.setup_ui()

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
        """UI initialization"""
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

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
        header_outer_layout = QHBoxLayout()
        header_outer_layout.setSpacing(0)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        self.header_label = QLabel("Conflict of Nations Replay Analyser")
        self.header_label.setObjectName("replay_list_page_header")
        header_layout.addWidget(self.header_label)

        self.subheader_label = QLabel("View and analyze your recorded game replays")
        self.subheader_label.setObjectName("replay_list_page_subheader")
        header_layout.addWidget(self.subheader_label)

        header_outer_layout.addLayout(header_layout)
        header_outer_layout.addStretch()

        # Settings button
        self.settings_btn = CIconButton("fa5s.cog", size=24, parent=self)
        self.settings_btn.setObjectName("settings_button")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(lambda: self.app.page_manager.switch_to(PageType.SettingsPage))
        header_outer_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignTop)

        # Download buttons row (below header text)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.download_replay_btn = CButton(
            "Download Replay from API",
            "outlined",
            "primary",
            "mdi.download",
            parent=self,
        )
        self.download_replay_btn.clicked.connect(self._on_download_replay_from_api)
        buttons_layout.addWidget(self.download_replay_btn)

        self.download_analysis_btn = CButton(
            "Download Analysis (Pro)",
            "outlined",
            "secondary",
            "mdi.google-analytics",
            parent=self,
        )
        self.download_analysis_btn.clicked.connect(self._on_download_analysis_from_api)
        buttons_layout.addWidget(self.download_analysis_btn)

        buttons_layout.addStretch()
        header_layout.addLayout(buttons_layout)

        parent_layout.addLayout(header_outer_layout)

    def page_update(self, delta_time: float):
        """Called every frame - check for changes and update if needed"""
        # Check if replay count has changed
        current_replay_count = len(self.app.replay_manager.get_replays())
        if current_replay_count != self._previous_replay_count:
            self._previous_replay_count = current_replay_count
            self.list_panel.refresh_list(self.app.replay_manager.get_replays())

        # Update Pro-only controls based on subscription status.
        auth = self.app.auth_manager
        api_online = self.app.api_client.last_ok is not False  # Treat None as \"unknown/assumed online\".
        if hasattr(self, "download_analysis_btn"):
            self.download_analysis_btn.setEnabled(api_online and auth.is_pro)
        if hasattr(self, "download_replay_btn"):
            self.download_replay_btn.setEnabled(api_online)

    def _update_details(self):
        """Update the details panel with selected replay info"""
        self.details_panel.update_details(self.selected_replay, self.selected_filepath)

    def _on_replay_selected(self, replay, filepath):
        """Handle replay selection change"""
        self.selected_replay = replay
        self.selected_filepath = filepath
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
            next_page=START_REPLAY_PAGE,
            replay_path=self.selected_filepath
        )

    def _ask_game_and_player_ids(self) -> tuple[str | None, str | None]:
        """Prompt the user for game ID and player ID."""
        game_id, ok = QInputDialog.getText(self, "Download from API", "Game ID:")
        if not ok or not game_id:
            return None, None

        player_id, ok = QInputDialog.getText(self, "Download from API", "Player ID:")
        if not ok or not player_id:
            return None, None

        return game_id.strip(), player_id.strip()

    def _default_replay_directory(self) -> str:
        """Return a directory path for storing downloaded replays."""
        import os

        default_path = self.app.config_manager.get("file.default_open_path", "")
        if default_path:
            directory = os.path.dirname(default_path)
            if directory:
                return directory
        return os.getcwd()

    def _download_replay_file(self, game_id: str, player_id: str) -> str | None:
        """Use the API to retrieve and download a replay file. Returns local path or None."""
        try:
            response = self.app.api_client.get(
                f"/downloads/replay/{game_id}/{player_id}",
                requires_auth=False,
            )
        except Exception as exc:
            logger.error(f"Failed to request replay download URL: {exc}")
            self._show_error_dialog(
                "Failed to fetch replay download URL from API.",
                str(exc),
            )
            return None

        url = response.get("url")
        if not url:
            self._show_error_dialog("API response did not contain a download URL.")
            return None

        directory = self._default_replay_directory()
        extension = self.app.config_manager.get("file.replay_file_extension", ".bin")
        filename = f"replay_{game_id}_{player_id}{extension}"

        import os

        dest_path = os.path.join(directory, filename)

        try:
            download_to_file(url, dest_path)
        except Exception as exc:
            logger.error(f"Failed to download replay file: {exc}")
            self._show_error_dialog(
                "Failed to download replay file from storage.",
                str(exc),
            )
            return None

        return dest_path

    def _download_analysis_file(self, game_id: str, player_id: str) -> str | None:
        """Use the API to retrieve and download an analysis file. Returns local path or None."""
        from conlyse.api import AuthError, PermissionError, ApiError, NetworkError

        try:
            response = self.app.api_client.get(
                f"/downloads/analysis/{game_id}/{player_id}",
                requires_auth=True,
            )
        except AuthError as exc:
            logger.error(f"Authentication required for analysis download: {exc}")
            self._show_error_dialog(
                "You must be signed in to download analysis files.",
                str(exc),
            )
            return None
        except PermissionError as exc:
            logger.error(f"Permission denied for analysis download: {exc}")
            self._show_error_dialog(
                "Downloading analysis files requires a Pro subscription.",
                str(exc),
            )
            return None
        except (ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to request analysis download URL: {exc}")
            self._show_error_dialog(
                "Failed to fetch analysis download URL from API.",
                str(exc),
            )
            return None

        url = response.get("url")
        if not url:
            self._show_error_dialog("API response did not contain a download URL.")
            return None

        directory = self._default_replay_directory()

        import os

        filename = f"analysis_{game_id}_{player_id}.bin"
        dest_path = os.path.join(directory, filename)

        try:
            download_to_file(url, dest_path)
        except Exception as exc:
            logger.error(f"Failed to download analysis file: {exc}")
            self._show_error_dialog(
                "Failed to download analysis file from storage.",
                str(exc),
            )
            return None

        return dest_path

    def _on_download_replay_from_api(self):
        """Prompt for identifiers and download a replay via the Conlyse API."""
        game_id, player_id = self._ask_game_and_player_ids()
        if not game_id or not player_id:
            return

        dest_path = self._download_replay_file(game_id, player_id)
        if not dest_path:
            return

        logger.debug(f"Downloaded replay to {dest_path}")
        success = self.app.replay_manager.add_replay(dest_path)
        if success:
            self._previous_replay_count = len(self.app.replay_manager.get_replays())
            self.selected_replay = self.app.replay_manager.get_replay(dest_path)
            self.selected_filepath = dest_path
            self.app.config_manager.set("file.default_open_path", dest_path)
            self.list_panel.refresh_list(self.app.replay_manager.get_replays())
            self._update_details()
        else:
            self._show_error_dialog(
                "Downloaded replay file could not be opened.",
                "The file may be corrupted or invalid.",
            )

    def _on_download_analysis_from_api(self):
        """Prompt for identifiers and download an analysis via the Conlyse API."""
        from conlyse.managers.auth_manager import AuthManager

        auth: AuthManager = self.app.auth_manager
        if not auth.is_authenticated:
            self._show_error_dialog(
                "Sign-in required",
                "You must sign in to your Conlyse account before downloading analysis files.",
            )
            return
        if not auth.is_pro:
            self._show_error_dialog(
                "Pro subscription required",
                "Downloading analysis files requires an active Pro subscription.",
            )
            return

        game_id, player_id = self._ask_game_and_player_ids()
        if not game_id or not player_id:
            return

        dest_path = self._download_analysis_file(game_id, player_id)
        if not dest_path:
            return

        logger.debug(f"Downloaded analysis to {dest_path}")
        # For now, the desktop client only stores analysis files locally.
        # Future versions can integrate them into the replay analysis workflows.

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
        # Cleanup panels
        if self.list_panel:
            self.list_panel.cleanup()

        # Clear references
        self.selected_replay = None
        self.selected_filepath = None

        self.app.keybinding_manager.unregister_action(KeyAction.OPEN_REPLAY_FILE_DIALOG)
