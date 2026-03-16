import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QTabWidget
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QInputDialog
from PySide6.QtWidgets import QWidget

from conlyse.api import ApiError, AuthError, NetworkError, PermissionError
from conlyse.constants import START_REPLAY_PAGE
from conlyse.logger import get_logger
from conlyse.managers.keybinding_manager.key_action import KeyAction
from conlyse.pages.page import Page
from conlyse.pages.replay_list_page.games_tab_panel import GamesTabPanel
from conlyse.pages.replay_list_page.recording_list_tab_panel import RecordingListTabPanel
from conlyse.pages.replay_list_page.replay_details_panel import ReplayDetailsPanel
from conlyse.pages.replay_list_page.replay_library_tab_panel import ReplayLibraryTabPanel
from conlyse.pages.replay_list_page.replay_list_panel import ReplayListPanel
from conlyse.utils.enums import PageType
from conlyse.utils.downloads import download_to_file
from conlyse.widgets.mui.icon_button import CIconButton
from conlyse.managers.config_manager.config_file import CONFIG_DIR

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
        self.tab_widget: QTabWidget | None = None
        self.games_tab: GamesTabPanel | None = None
        self.recording_list_tab: RecordingListTabPanel | None = None
        self.replay_library_tab: ReplayLibraryTabPanel | None = None
        self.local_tab: QWidget | None = None
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

        # Content area: tabbed layout
        self.tab_widget = QTabWidget(self)

        # Games tab
        self.games_tab = GamesTabPanel(self)
        self.games_tab.set_callbacks(
            on_refresh=self._refresh_games_tab,
            on_add_to_recording_list=self._add_game_to_recording_list_from_games,
            on_add_to_replay_library=self._add_game_to_replay_library_from_games,
        )
        self.tab_widget.addTab(self.games_tab, "Games")

        # Recording List tab
        self.recording_list_tab = RecordingListTabPanel(self)
        self.recording_list_tab.set_callbacks(
            on_refresh=self._refresh_recording_list_tab,
            on_add_by_game_id=self._add_recording_list_entry_from_tab,
            on_remove=self._remove_recording_list_entry_from_tab,
            on_add_to_replay_library=self._add_game_to_replay_library_from_recording_tab,
        )
        self.tab_widget.addTab(self.recording_list_tab, "Recording List")

        # Replay Library tab
        self.replay_library_tab = ReplayLibraryTabPanel(self)
        self.replay_library_tab.set_callbacks(
            on_refresh=self._refresh_replay_library_tab,
            on_download_replay=self._download_replay_for_library_game,
        )
        self.tab_widget.addTab(self.replay_library_tab, "Replay Library")

        # Local Games tab (reuses existing list + details panels)
        self.local_tab = QWidget(self)
        local_layout = QHBoxLayout(self.local_tab)
        local_layout.setSpacing(24)

        # Left side - Replay list
        self.list_panel = ReplayListPanel()
        self.list_panel.set_callbacks(
            on_open=self.on_open_replay,
            on_selection_changed=self._on_replay_selected,
        )
        local_layout.addWidget(self.list_panel)

        # Right side - Details
        self.details_panel = ReplayDetailsPanel()
        self.details_panel.set_callbacks(
            on_analyze=self._on_analyze_clicked,
            on_delete=self._on_delete_clicked,
        )
        local_layout.addWidget(self.details_panel)

        self.tab_widget.addTab(self.local_tab, "Local Games")

        main_layout.addWidget(self.tab_widget)

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

        parent_layout.addLayout(header_outer_layout)

    def page_update(self, delta_time: float):
        """Called every frame - check for changes and update if needed"""
        # Check if replay count has changed (Local Games tab)
        if self.tab_widget and self.local_tab and self.tab_widget.currentWidget() is self.local_tab:
            current_replay_count = len(self.app.replay_manager.get_replays())
            if current_replay_count != self._previous_replay_count:
                self._previous_replay_count = current_replay_count
                if self.list_panel:
                    self.list_panel.refresh_list(self.app.replay_manager.get_replays())

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

    def _ask_game_id(self, title: str) -> str | None:
        game_id, ok = QInputDialog.getText(self, title, "Game ID:")
        if not ok or not game_id:
            return None
        return game_id.strip()

    def _default_replay_directory(self) -> str:
        """Return a directory path for storing downloaded replays.

        Downloaded replays are stored under the app_data/replays directory to keep
        them alongside other application data.
        """
        base_dir = Path(CONFIG_DIR) / "replays"
        base_dir.mkdir(parents=True, exist_ok=True)
        return str(base_dir)

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


    # ------------------------------------------------------------------ #
    # Games tab helpers
    # ------------------------------------------------------------------ #

    def _refresh_games_tab(self):
        """Load games discovered by the observer into the Games tab."""
        if not self.games_tab:
            return

        try:
            games = self.app.api_client.get("/games", requires_auth=True)
        except (AuthError, PermissionError, ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to fetch games: {exc}")
            self._show_error_dialog("Failed to fetch games from API.", str(exc))
            return

        self.games_tab.update_games(games or [])

    def _add_game_to_recording_list_from_games(self, game_id: int):
        """Add a game to the recording list from the Games tab."""
        try:
            self.app.api_client.post(
                "/recording-list",
                requires_auth=True,
                json={"game_id": int(game_id)},
            )
        except (AuthError, PermissionError, ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to add game to recording list: {exc}")
            self._show_error_dialog("Failed to add game to recording list.", str(exc))
            return

        QMessageBox.information(self, "Recording List", f"Game {game_id} added to recording list.")
        # Keep recording list tab up to date if user switches to it.
        if self.recording_list_tab:
            self._refresh_recording_list_tab()

    def _add_game_to_replay_library_from_games(self, game_id: int):
        """Add a game to the replay library from the Games tab."""
        try:
            self.app.api_client.post(
                "/replay-library",
                requires_auth=True,
                json={"game_id": int(game_id)},
            )
        except (AuthError, PermissionError, ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to add game to replay library: {exc}")
            self._show_error_dialog("Failed to add game to replay library.", str(exc))
            return

        QMessageBox.information(self, "Replay Library", f"Game {game_id} added to replay library.")
        if self.replay_library_tab:
            self._refresh_replay_library_tab()

    # ------------------------------------------------------------------ #
    # Recording List tab helpers
    # ------------------------------------------------------------------ #

    def _refresh_recording_list_tab(self):
        """Refresh the recording list tab with the current user's recording list."""
        if not self.recording_list_tab:
            return

        try:
            items = self.app.api_client.get("/recording-list", requires_auth=True)
        except (AuthError, PermissionError, ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to fetch recording list: {exc}")
            self._show_error_dialog("Failed to fetch recording list from API.", str(exc))
            return

        self.recording_list_tab.update_items(items or [])

    def _add_recording_list_entry_from_tab(self):
        """Prompt for a game ID and add it to the recording list, then refresh."""
        game_id = self._ask_game_id("Add to Recording List")
        if not game_id:
            return

        try:
            self.app.api_client.post(
                "/recording-list",
                requires_auth=True,
                json={"game_id": int(game_id)},
            )
        except (AuthError, PermissionError, ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to add game to recording list: {exc}")
            self._show_error_dialog("Failed to add game to recording list.", str(exc))
            return

        QMessageBox.information(self, "Recording List", f"Game {game_id} added to recording list.")
        self._refresh_recording_list_tab()

    def _remove_recording_list_entry_from_tab(self, game_id: int):
        """Remove a game from the recording list, then refresh."""
        try:
            self.app.api_client.delete(
                f"/recording-list/{int(game_id)}",
                requires_auth=True,
                expects_body=False,
            )
        except (AuthError, PermissionError, ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to remove game from recording list: {exc}")
            self._show_error_dialog("Failed to remove game from recording list.", str(exc))
            return

        QMessageBox.information(
            self, "Recording List", f"Game {game_id} removed from recording list."
        )
        self._refresh_recording_list_tab()

    def _add_game_to_replay_library_from_recording_tab(self, game_id: int):
        """Add a game from the recording list tab to the replay library."""
        try:
            self.app.api_client.post(
                "/replay-library",
                requires_auth=True,
                json={"game_id": int(game_id)},
            )
        except (AuthError, PermissionError, ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to add game to replay library: {exc}")
            self._show_error_dialog("Failed to add game to replay library.", str(exc))
            return

        QMessageBox.information(self, "Replay Library", f"Game {game_id} added to replay library.")
        self._refresh_replay_library_tab()

    # ------------------------------------------------------------------ #
    # Replay Library tab helpers
    # ------------------------------------------------------------------ #

    def _refresh_replay_library_tab(self):
        """Refresh the replay library tab with the current user's library entries."""
        if not self.replay_library_tab:
            return

        try:
            items = self.app.api_client.get("/replay-library", requires_auth=True)
        except (AuthError, PermissionError, ApiError, NetworkError, Exception) as exc:
            logger.error(f"Failed to fetch replay library: {exc}")
            self._show_error_dialog("Failed to fetch replay library from API.", str(exc))
            return

        self.replay_library_tab.update_items(items or [])

    def _download_replay_for_library_game(self, game_id: int):
        """Download a replay for a game from the replay library tab."""
        # Game ID is known; ask only for player ID.
        player_id, ok = QInputDialog.getText(self, "Download Replay", "Player ID:")
        if not ok or not player_id:
            return

        dest_path = self._download_replay_file(str(game_id), player_id.strip())
        if not dest_path:
            return

        logger.debug(f"Downloaded replay for game {game_id} to {dest_path}")
        success = self.app.replay_manager.add_replay(dest_path)
        if success:
            self._previous_replay_count = len(self.app.replay_manager.get_replays())
            self.selected_replay = self.app.replay_manager.get_replay(dest_path)
            self.selected_filepath = dest_path
            self.app.config_manager.set("file.default_open_path", dest_path)
            if self.list_panel:
                self.list_panel.refresh_list(self.app.replay_manager.get_replays())
            self._update_details()
        else:
            self._show_error_dialog(
                "Downloaded replay file could not be opened.",
                "The file may be corrupted or invalid.",
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
        # Cleanup panels
        if self.list_panel:
            self.list_panel.cleanup()

        # Clear references
        self.selected_replay = None
        self.selected_filepath = None

        self.app.keybinding_manager.unregister_action(KeyAction.OPEN_REPLAY_FILE_DIALOG)
