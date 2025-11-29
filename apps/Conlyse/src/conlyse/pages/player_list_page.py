"""
Player List Page
================
Displays a list of players from a replay using the MUI Data Grid.
Shows player attributes, team information, and statistics.

Author: NikNam3
Date: 2025-11-18
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QMessageBox
from PyQt6.QtCore import Qt

from conlyse.logger import get_logger
from conlyse.pages.page import Page
from conlyse.utils.enums import PageType
from conlyse.widgets.table_widget.mui_data_grid import MUIDataGrid

if TYPE_CHECKING:
    from conlyse.app import App
    from conlyse.managers.replay_manager import ReplayInterface

logger = get_logger()


class PlayerListPage(Page):
    """Page displaying list of players from a replay with detailed information."""

    HEADER = True

    def __init__(self, app, parent=None):
        super().__init__(parent)

        self.app: App = app
        self.replay_interface: Optional[ReplayInterface] = None

        # Data grid and components
        self.data_grid: Optional[MUIDataGrid] = None
        self.info_label: Optional[QLabel] = None
        self.back_button: Optional[QPushButton] = None
        self.export_button: Optional[QPushButton] = None

        # Track if UI has been set up
        self._ui_initialized = False

        # Player data cache
        self._players_data = []

    def setup(self, context):
        """
        Called when page is opened - initialize with replay data.

        Args:
            context: Dictionary containing 'replay_interface' key
        """
        replay_path = context.get("replay_path", None)

        if not replay_path:
            logger.error("No replay interface provided to PlayerListPage")
            self.app.page_manager.switch_to(PageType.ReplayListPage)

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("No Replay Data")
            msg_box.setText("No replay data available to display players.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return

        self.replay_interface = self.app.replay_manager.get_replay(replay_path)

        if not self.app.replay_manager.is_open_replay(replay_path):
            logger.error(f"Replay not loaded for path: {replay_path}")
            self.app.page_manager.switch_to(PageType.ReplayListPage, error_message=f"Failed to load replay: {replay_path}")
            return


        # Initialize UI if first time
        if not self._ui_initialized:
            self._setup_ui()
            self._ui_initialized = True

        # Load player data
        self._load_player_data()

        logger.info(f"PlayerListPage setup complete with {len(self._players_data)} players")

    def _setup_ui(self):
        """One-time UI initialization."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # ===== Header Section =====
        header_layout = QHBoxLayout()

        # Title and info
        title_label = QLabel("Players")
        title_label.setObjectName("player_list_title")
        header_layout.addWidget(title_label)

        self.info_label = QLabel()
        self.info_label.setObjectName("player_list_info")
        header_layout.addWidget(self.info_label)

        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ===== Data Grid =====
        self.data_grid = MUIDataGrid()
        self.data_grid.setObjectName("player_list_grid")
        main_layout.addWidget(self.data_grid, stretch=1)

        # ===== Setup Custom Renderers =====
        self._setup_renderers()
        self._setup_extractors()

    def _setup_renderers(self):
        """Set up custom cell renderers for the data grid."""

        # ===== Boolean Renderer (for checkmarks) =====
        def render_boolean(value, row_data, row_index):
            label = QLabel("✓" if value else "✗")
            label.setObjectName("boolean_cell_true" if value else "boolean_cell_false")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return label

        # ===== Faction Renderer (with icon and text) =====
        def render_faction(value, row_data, row_index):
            container = QWidget()
            container.setObjectName("faction_cell")
            layout = QHBoxLayout(container)
            layout.setContentsMargins(4, 2, 4, 2)
            layout.setSpacing(6)

            # Faction icons and names
            faction_info = {
                "WESTERN": ("🌎", "Western"),
                "EASTERN": ("🌏", "Eastern"),
                "EUROPEAN": ("🇪🇺", "European"),
                "NONE": ("⚪", "None")
            }

            faction_str = str(value) if isinstance(value, str) else value.name if hasattr(value, 'name') else "NONE"
            icon, name = faction_info.get(faction_str, ("⚪", faction_str))

            icon_label = QLabel(icon)
            icon_label.setObjectName("faction_icon")

            text_label = QLabel(name)
            text_label.setObjectName("faction_text")

            layout.addWidget(icon_label)
            layout.addWidget(text_label)
            layout.addStretch()

            return container

        # ===== Victory Points Renderer (formatted numbers) =====
        def render_victory_points(value, row_data, row_index):
            label = QLabel(f"{value:,}")
            label.setObjectName("victory_points_cell")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return label

        # ===== Optional String Renderer (handles None) =====
        def render_optional_string(value, row_data, row_index):
            text = value if value is not None else "N/A"
            label = QLabel(text)
            label.setObjectName("optional_string_cell")
            return label

        # ===== Optional Boolean Renderer (handles None) =====
        def render_optional_boolean(value, row_data, row_index):
            if value is None:
                text = "?"
                obj_name = "optional_boolean_unknown"
            elif value:
                text = "✓"
                obj_name = "optional_boolean_true"
            else:
                text = "✗"
                obj_name = "optional_boolean_false"

            label = QLabel(text)
            label.setObjectName(obj_name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return label

        # ===== Register Renderers =====
        # Boolean columns
        self.data_grid.set_cell_renderer("ComputerPlayer", render_boolean)
        self.data_grid.set_cell_renderer("NativeComputer", render_boolean)
        self.data_grid.set_cell_renderer("Defeated", render_boolean)
        self.data_grid.set_cell_renderer("Retired", render_boolean)
        self.data_grid.set_cell_renderer("Playing", render_boolean)
        self.data_grid.set_cell_renderer("Taken", render_boolean)
        self.data_grid.set_cell_renderer("Available", render_boolean)
        self.data_grid.set_cell_renderer("TerroristCountry", render_boolean)
        self.data_grid.set_cell_renderer("Banned", render_boolean)

        # Optional boolean columns
        self.data_grid.set_cell_renderer("PremiumUser", render_optional_boolean)

        # Faction column
        self.data_grid.set_cell_renderer("Faction", render_faction)

        # Victory points columns
        self.data_grid.set_cell_renderer("AccumulatedVictoryPoints", render_victory_points)
        self.data_grid.set_cell_renderer("DailyVictoryPoints", render_victory_points)
        self.data_grid.set_cell_renderer("VictoryPoints", render_victory_points)

        # Optional string columns
        self.data_grid.set_cell_renderer("UserName", render_optional_string)

    def _setup_extractors(self):
        """Set up filter and search value extractors."""

        # ===== Boolean Extractors =====
        def extract_boolean(value, row_data):
            return "yes true 1" if value else "no false 0"

        # ===== Optional Boolean Extractors =====
        def extract_optional_boolean(value, row_data):
            if value is None:
                return "unknown none null"
            return "yes true 1" if value else "no false 0"

        # ===== Faction Extractors =====
        def extract_faction(value, row_data):
            if isinstance(value, str):
                return value.lower()
            return value.name.lower() if hasattr(value, 'name') else "none"

        # ===== Victory Points Extractors =====
        def extract_victory_points(value, row_data):
            return value  # Keep as number for numeric comparisons

        def search_victory_points(value, row_data):
            return f"{value} {value:,} vp victory points"

        # ===== Optional String Extractors =====
        def extract_optional_string(value, row_data):
            return str(value).lower() if value is not None else "n/a none null empty"

        # ===== Register Filter Extractors =====
        # Boolean columns
        self.data_grid.set_filter_value_extractor("ComputerPlayer", extract_boolean)
        self.data_grid.set_filter_value_extractor("NativeComputer", extract_boolean)
        self.data_grid.set_filter_value_extractor("Defeated", extract_boolean)
        self.data_grid.set_filter_value_extractor("Retired", extract_boolean)
        self.data_grid.set_filter_value_extractor("Playing", extract_boolean)
        self.data_grid.set_filter_value_extractor("Taken", extract_boolean)
        self.data_grid.set_filter_value_extractor("Available", extract_boolean)
        self.data_grid.set_filter_value_extractor("TerroristCountry", extract_boolean)
        self.data_grid.set_filter_value_extractor("Banned", extract_boolean)

        # Optional boolean
        self.data_grid.set_filter_value_extractor("PremiumUser", extract_optional_boolean)

        # Faction
        self.data_grid.set_filter_value_extractor("Faction", extract_faction)

        # Victory points
        self.data_grid.set_filter_value_extractor("AccumulatedVictoryPoints", extract_victory_points)
        self.data_grid.set_filter_value_extractor("DailyVictoryPoints", extract_victory_points)
        self.data_grid.set_filter_value_extractor("VictoryPoints", extract_victory_points)

        # Optional string
        self.data_grid.set_filter_value_extractor("UserName", extract_optional_string)

        # ===== Register Search Extractors =====
        # Boolean columns
        self.data_grid.set_search_value_extractor("ComputerPlayer", extract_boolean)
        self.data_grid.set_search_value_extractor("NativeComputer", extract_boolean)
        self.data_grid.set_search_value_extractor("Defeated", extract_boolean)
        self.data_grid.set_search_value_extractor("Retired", extract_boolean)
        self.data_grid.set_search_value_extractor("Playing", extract_boolean)
        self.data_grid.set_search_value_extractor("Taken", extract_boolean)
        self.data_grid.set_search_value_extractor("Available", extract_boolean)
        self.data_grid.set_search_value_extractor("TerroristCountry", extract_boolean)
        self.data_grid.set_search_value_extractor("Banned", extract_boolean)

        # Optional boolean
        self.data_grid.set_search_value_extractor("PremiumUser", extract_optional_boolean)

        # Faction
        self.data_grid.set_search_value_extractor("Faction", extract_faction)

        # Victory points
        self.data_grid.set_search_value_extractor("AccumulatedVictoryPoints", search_victory_points)
        self.data_grid.set_search_value_extractor("DailyVictoryPoints", search_victory_points)
        self.data_grid.set_search_value_extractor("VictoryPoints", search_victory_points)

        # Optional string
        self.data_grid.set_search_value_extractor("UserName", extract_optional_string)

    def _load_player_data(self):
        """Load player data from replay interface into grid format."""
        if not self.replay_interface:
            return

        try:
            # Get players from replay interface
            players = self.replay_interface.get_players().values()  # Adjust method name as needed

            # Convert PlayerProfile objects to dictionaries
            self._players_data = []

            for player in players:
                team = self.replay_interface.get_team(player.team_id)
                capital = self.replay_interface.get_province(player.capital_id)
                team_name = team.name if team else "N/A"
                capital_name = capital.name if capital else "N/A"
                player_dict = {
                    # All attributes as separate columns
                    "PlayerID": player.player_id,
                    "TeamName": team_name,
                    "Name": player.name,
                    "CapitalName": capital_name,
                    "NationName": player.nation_name,
                    "ComputerPlayer": player.computer_player,
                    "NativeComputer": player.native_computer,
                    "UserName": player.user_name,
                    "Defeated": player.defeated,
                    "Retired": player.retired,
                    "Playing": player.playing,
                    "Taken": player.taken,
                    "Faction": player.faction,
                    "Available": player.available,
                    "PremiumUser": player.premium_user,
                    "AccumulatedVictoryPoints": player.accumulated_victory_points,
                    "DailyVictoryPoints": player.daily_victory_points,
                    "TerroristCountry": player.terrorist_country,
                    "Banned": player.banned,
                    "VictoryPoints": player.victory_points,
                }

                self._players_data.append(player_dict)

            # Define all visible columns (one for each attribute)
            visible_columns = [
                "PlayerID",
                "TeamName",
                "Name",
                "CapitalName",
                "NationName",
                "ComputerPlayer",
                "NativeComputer",
                "UserName",
                "Defeated",
                "Retired",
                "Playing",
                "Taken",
                "Faction",
                "Available",
                "PremiumUser",
                "AccumulatedVictoryPoints",
                "DailyVictoryPoints",
                "TerroristCountry",
                "Banned",
                "VictoryPoints",
            ]

            # Load into data grid
            self.data_grid.set_data(self._players_data, columns=visible_columns)

            # Update info label
            human_count = sum(1 for p in players if not p.computer_player)
            ai_count = sum(1 for p in players if p.computer_player)
            native_ai_count = sum(1 for p in players if p.computer_player and p.native_computer)
            playing_count = sum(1 for p in players if p.playing)
            defeated_count = sum(1 for p in players if p.defeated)

            self.info_label.setText(
                f"Total: {len(players)} | "
                f"Human: {human_count} | "
                f"AI: {ai_count} (Native: {native_ai_count}) | "
                f"Playing: {playing_count} | "
                f"Defeated: {defeated_count}"
            )

            logger.info(f"Loaded {len(players)} players into grid")

        except Exception as e:
            logger.error(f"Error loading player data: {e}", exc_info=True)

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error Loading Players")
            msg_box.setText(f"Failed to load player data: {str(e)}")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

    def update(self):
        """Called every frame - no continuous updates needed for this page."""
        pass

    def clean_up(self):
        """Called when page is closed - cleanup resources."""
        logger.debug("PlayerListPage cleanup")

        # Clear data
        self._players_data = []
        self.replay_interface = None

        # No need to destroy widgets, they will be handled by Qt parent-child relationship

    # ==========================================================================
    # EVENT HANDLERS
    # ==========================================================================

    def _on_back_clicked(self):
        """Handle back button click."""
        logger.info("Navigating back to replay list")
        self.app.page_manager.switch_to(PageType.ReplayListPage)

    def _on_export_clicked(self):
        """Handle export button click."""
        logger.info("Export player data requested")

        # Get filtered data
        filtered_data = self.data_grid.get_all_filtered_data()

        if not filtered_data:
            QMessageBox.information(
                self,
                "No Data",
                "No player data to export."
            )
            return

        # TODO: Implement CSV export
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Export")
        msg.setText(f"Export {len(filtered_data)} players")
        msg.setInformativeText("CSV export functionality will be implemented here.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()