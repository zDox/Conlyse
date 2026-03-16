from __future__ import annotations

from typing import Callable, Iterable, Mapping, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from conlyse.widgets.mui.button import CButton


class GamesTabPanel(QWidget):
    """Tab showing all games discovered by the server_observer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._on_refresh: Callable[[], None] | None = None
        self._on_add_to_recording_list: Callable[[int], None] | None = None
        self._on_add_to_replay_library: Callable[[int], None] | None = None

        self.header_label: QLabel | None = None
        self.badge_label: QLabel | None = None
        self.table: QTableWidget | None = None
        self.empty_label: QLabel | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self.header_label = QLabel("Games")
        self.header_label.setObjectName("replay_games_header")
        header_layout.addWidget(self.header_label)

        self.badge_label = QLabel("0")
        self.badge_label.setObjectName("replay_games_badge")
        self.badge_label.setMaximumWidth(60)
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.badge_label)

        header_layout.addStretch()

        refresh_btn = CButton(
            "Refresh",
            "outlined",
            "primary",
            icon_name="mdi.refresh",
            parent=self,
        )
        refresh_btn.clicked.connect(self._handle_refresh_clicked)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        separator = QFrame(self)
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        self.table = QTableWidget(self)
        self.table.setObjectName("replay_games_table")
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "Game ID",
                "Scenario ID",
                "Status",
                "Discovered",
                "Started",
                "Completed",
                "Actions",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.empty_label = QLabel("No games discovered yet by the observer.")
        self.empty_label.setObjectName("replay_games_empty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

    def set_callbacks(
        self,
        on_refresh: Callable[[], None] | None = None,
        on_add_to_recording_list: Callable[[int], None] | None = None,
        on_add_to_replay_library: Callable[[int], None] | None = None,
    ) -> None:
        self._on_refresh = on_refresh
        self._on_add_to_recording_list = on_add_to_recording_list
        self._on_add_to_replay_library = on_add_to_replay_library

    def update_games(self, games: Iterable[Mapping[str, Any]]) -> None:
        """Replace the table contents with the provided games list."""
        if self.table is None or self.badge_label is None or self.empty_label is None:
            return

        games_list = list(games)
        self.table.setRowCount(len(games_list))

        for row, game in enumerate(games_list):
            game_id = int(game.get("game_id", 0))
            scenario_id = int(game.get("scenario_id", 0))
            status = str(game.get("status", "unknown"))
            discovered = str(game.get("discovered_date", ""))
            started = str(game.get("started_date", "")) if game.get("started_date") else ""
            completed = str(game.get("completed_date", "")) if game.get("completed_date") else ""

            self.table.setItem(row, 0, QTableWidgetItem(str(game_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(scenario_id)))
            self.table.setItem(row, 2, QTableWidgetItem(status))
            self.table.setItem(row, 3, QTableWidgetItem(discovered))
            self.table.setItem(row, 4, QTableWidgetItem(started))
            self.table.setItem(row, 5, QTableWidgetItem(completed))

            actions_widget = QWidget(self.table)
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(6)

            add_recording_btn = CButton(
                "To Recording",
                "text",
                "primary",
                icon_name="mdi.playlist-plus",
                parent=actions_widget,
            )
            add_recording_btn.clicked.connect(
                lambda _checked=False, gid=game_id: self._handle_add_to_recording_list(gid)
            )
            actions_layout.addWidget(add_recording_btn)

            add_library_btn = CButton(
                "To Library",
                "text",
                "secondary",
                icon_name="mdi.library",
                parent=actions_widget,
            )
            add_library_btn.clicked.connect(
                lambda _checked=False, gid=game_id: self._handle_add_to_replay_library(gid)
            )
            actions_layout.addWidget(add_library_btn)

            actions_layout.addStretch()
            self.table.setCellWidget(row, 6, actions_widget)

        self.badge_label.setText(str(len(games_list)))
        self.empty_label.setVisible(len(games_list) == 0)
        self.table.setVisible(len(games_list) > 0)

    # --------------------------------------------------------------------- #
    # Internal handlers
    # --------------------------------------------------------------------- #

    def _handle_refresh_clicked(self) -> None:
        if self._on_refresh:
            self._on_refresh()

    def _handle_add_to_recording_list(self, game_id: int) -> None:
        if self._on_add_to_recording_list:
            self._on_add_to_recording_list(game_id)

    def _handle_add_to_replay_library(self, game_id: int) -> None:
        if self._on_add_to_replay_library:
            self._on_add_to_replay_library(game_id)

