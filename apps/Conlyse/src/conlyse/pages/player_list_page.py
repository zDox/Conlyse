"""
Player List Page
================
Displays a list of players from a replay using the MUI Data Grid.
Shows player attributes, team information, and statistics.

Author: NikNam3
Date: 2025-11-18
"""

from __future__ import annotations

import time
from typing import Optional
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget
from conflict_interface.data_types.player_state.player_profile import PlayerProfile
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag

from conlyse.logger import get_logger
from conlyse.pages.replay_page import ReplayPage
from conlyse.utils.enums import PageType
from conlyse.widgets.table_widget.mui_data_grid import MUIDataGrid

if TYPE_CHECKING:
    from conlyse.app import App
    from conlyse.managers.replay_manager import ReplayInterface

logger = get_logger()


class PlayerListPage(ReplayPage):
    """Page displaying list of players from a replay with detailed information."""
    HEADER = True

    # Mapping between display column names and PlayerProfile attribute names
    # Format: "DisplayName": "attribute_name"
    # Special cases: "TeamName", "CapitalName", "NationName" are computed fields
    COLUMN_MAPPING = {
        "PlayerID": "player_id",
        "TeamName": None,  # Computed from team_id
        "Name": "name",
        "CapitalName": None,  # Computed from capital_id
        "NationName": "nation_name",
        "ComputerPlayer": "computer_player",
        "NativeComputer": "native_computer",
        "UserName": "user_name",
        "Defeated": "defeated",
        "Retired": "retired",
        "Playing": "playing",
        "Taken": "taken",
        "Faction": "faction",
        "Available": "available",
        "PremiumUser": "premium_user",
        "AccumulatedVictoryPoints": "accumulated_victory_points",
        "DailyVictoryPoints": "daily_victory_points",
        "TerroristCountry": "terrorist_country",
        "Banned": "banned",
        "VictoryPoints": "victory_points",
    }

    # Column types for renderer assignment
    BOOLEAN_COLUMNS = [
        "ComputerPlayer", "NativeComputer", "Defeated", "Retired",
        "Playing", "Taken", "Available", "TerroristCountry", "Banned"
    ]
    OPTIONAL_BOOLEAN_COLUMNS = ["PremiumUser"]
    FACTION_COLUMNS = ["Faction"]
    VICTORY_POINTS_COLUMNS = ["AccumulatedVictoryPoints", "DailyVictoryPoints", "VictoryPoints"]
    OPTIONAL_STRING_COLUMNS = ["UserName"]

    def __init__(self, app, parent=None):
        super().__init__(app, parent)

        # Data grid and components
        self.data_grid: Optional[MUIDataGrid] = None
        self.info_label: Optional[QLabel] = None
        self.back_button: Optional[QPushButton] = None
        self.export_button: Optional[QPushButton] = None

        self.last_time = 0.0
        # Track if UI has been set up
        self._ui_initialized = False

        # Player data cache and mapping
        self._players_data = []
        # Map player_id to index in _players_data for O(1) lookups
        self._player_id_to_index = {}

    def setup(self, context):
        """
        Called when page is opened - initialize with replay data.
        """
        super().setup(context)

        # Initialize UI if first time
        if not self._ui_initialized:
            self._setup_ui()
            self._ui_initialized = True

        # Load player data
        self._load_player_data()

        # Register triggers for all PlayerProfile attributes (excluding computed fields)
        trigger_attributes = [
            attr_name for attr_name in self.COLUMN_MAPPING.values()
            if attr_name is not None
        ]
        self.ritf.register_player_trigger(trigger_attributes)

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
        title_label = QLabel("Players", self)
        title_label.setObjectName("player_list_title")
        header_layout.addWidget(title_label)

        self.info_label = QLabel(self)
        self.info_label.setObjectName("player_list_info")
        header_layout.addWidget(self.info_label)

        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ===== Data Grid =====
        self.data_grid = MUIDataGrid(self)
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
        for col in self.BOOLEAN_COLUMNS:
            self.data_grid.set_cell_renderer(col, render_boolean)

        # Optional boolean columns
        for col in self.OPTIONAL_BOOLEAN_COLUMNS:
            self.data_grid.set_cell_renderer(col, render_optional_boolean)

        # Faction column
        self.data_grid.set_cell_renderer("Faction", render_faction)

        # Victory points columns
        for col in self.VICTORY_POINTS_COLUMNS:
            self.data_grid.set_cell_renderer(col, render_victory_points)

        # Optional string columns
        for col in self.OPTIONAL_STRING_COLUMNS:
            self.data_grid.set_cell_renderer(col, render_optional_string)

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
        for col in self.BOOLEAN_COLUMNS:
            self.data_grid.set_filter_value_extractor(col, extract_boolean)

        # Optional boolean
        for col in self.OPTIONAL_BOOLEAN_COLUMNS:
            self.data_grid.set_filter_value_extractor(col, extract_optional_boolean)

        # Faction
        self.data_grid.set_filter_value_extractor("Faction", extract_faction)

        # Victory points
        for col in self.VICTORY_POINTS_COLUMNS:
            self.data_grid.set_filter_value_extractor(col, extract_victory_points)

        # Optional string
        for col in self.OPTIONAL_STRING_COLUMNS:
            self.data_grid.set_filter_value_extractor(col, extract_optional_string)

        # ===== Register Search Extractors =====
        # Boolean columns
        for col in self.BOOLEAN_COLUMNS:
            self.data_grid.set_search_value_extractor(col, extract_boolean)

        # Optional boolean
        for col in self.OPTIONAL_BOOLEAN_COLUMNS:
            self.data_grid.set_search_value_extractor(col, extract_optional_boolean)

        # Faction
        self.data_grid.set_search_value_extractor("Faction", extract_faction)

        # Victory points
        for col in self.VICTORY_POINTS_COLUMNS:
            self.data_grid.set_search_value_extractor(col, search_victory_points)

        # Optional string
        for col in self.OPTIONAL_STRING_COLUMNS:
            self.data_grid.set_search_value_extractor(col, extract_optional_string)

    def _load_player_data(self):
        """Load player data from replay interface into grid format."""
        if not self.ritf:
            return

        try:
            # Get players from replay interface
            players = self.ritf.get_players().values()

            # Convert PlayerProfile objects to dictionaries
            self._players_data = []
            self._player_id_to_index = {}

            for idx, player in enumerate(players):
                player_dict = {}

                # Iterate through column mapping to build player dict
                for display_name, attr_name in self.COLUMN_MAPPING.items():
                    if attr_name is None:
                        # Handle computed fields
                        if display_name == "TeamName":
                            team = self.ritf.get_team(player.team_id)
                            player_dict[display_name] = team.name if team else "N/A"
                        elif display_name == "CapitalName":
                            capital = self.ritf.get_province(player.capital_id)
                            player_dict[display_name] = capital.name if capital else "N/A"
                    else:
                        # Get attribute directly from PlayerProfile
                        player_dict[display_name] = getattr(player, attr_name)

                self._players_data.append(player_dict)
                # Build mapping for efficient updates
                self._player_id_to_index[player.player_id] = idx

            # Get visible columns from mapping keys (maintains order)
            visible_columns = list(self.COLUMN_MAPPING.keys())

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

    def page_update(self, delta_time: float):
        """Called every frame - no continuous updates needed for this page."""
        super().page_update(delta_time)

    def _on_replay_jump(self):
        """
        Efficiently update player data when replay jumps to a different time.
        Only updates players that have changed, avoiding full data reload.
        """
        if not self.ritf or not self._players_data:
            return

        events = self.ritf.poll_events()
        if ReplayHookTag.PlayerChanged not in events:
            return  # No player changes, skip update

        updates = []
        for event in events[ReplayHookTag.PlayerChanged]:
            player: PlayerProfile = event.reference

            # Get the row index for this player
            row_idx = self._player_id_to_index.get(player.player_id)
            if row_idx is None:
                # Player not in our data - log for debugging
                logger.warning(f"Player {player.player_id} not found in index mapping during replay jump")
                continue

            # Get current data
            current_data = self._players_data[row_idx]

            # Build updated data dict using COLUMN_MAPPING
            updated_data = {}
            changed_attrs = {key for key, _ in event.attributes.items()}

            for display_name, attr_name in self.COLUMN_MAPPING.items():
                # Check if this attribute or its dependencies changed
                if attr_name is None:
                    # Handle computed fields
                    if display_name == "TeamName" and "team_id" in changed_attrs:
                        team = self.ritf.get_team(player.team_id)
                        updated_data[display_name] = team.name if team else "N/A"
                    elif display_name == "CapitalName" and "capital_id" in changed_attrs:
                        capital = self.ritf.get_province(player.capital_id)
                        updated_data[display_name] = capital.name if capital else "N/A"
                elif attr_name in changed_attrs:
                    # Get updated attribute value from PlayerProfile
                    updated_data[display_name] = getattr(player, attr_name)

            updates.append((row_idx, updated_data))
            # Update our cache
            current_data.update(updated_data)

        if not updates:
            return  # No actual changes detected

        # Apply all updates in a single batch operation
        self.data_grid.update_rows_batch(updates)


    def clean_up(self):
        """Called when page is closed - cleanup resources."""
        super().clean_up()
        # Clear data
        self._players_data = []
        self._player_id_to_index = {}
        self.ritf.unregister_player_trigger()

        # No need to destroy widgets, they will be handled by Qt parent-child relationship