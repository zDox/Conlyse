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


class ReplayLibraryTabPanel(QWidget):
    """Tab showing the user's replay library entries."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._on_refresh: Callable[[], None] | None = None
        self._on_download_replay: Callable[[int], None] | None = None

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

        self.header_label = QLabel("Replay Library")
        self.header_label.setObjectName("replay_library_header")
        header_layout.addWidget(self.header_label)

        self.badge_label = QLabel("0")
        self.badge_label.setObjectName("replay_library_badge")
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
        self.table.setObjectName("replay_library_table")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            [
                "Game ID",
                "Scenario ID",
                "Added At",
                "Actions",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.empty_label = QLabel(
            "Your replay library is empty. Add completed games from the Games or Recording List tabs."
        )
        self.empty_label.setObjectName("replay_library_empty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

    def set_callbacks(
        self,
        on_refresh: Callable[[], None] | None = None,
        on_download_replay: Callable[[int], None] | None = None,
    ) -> None:
        self._on_refresh = on_refresh
        self._on_download_replay = on_download_replay

    def update_items(self, items: Iterable[Mapping[str, Any]]) -> None:
        """Replace the table contents with the provided replay library items."""
        if self.table is None or self.badge_label is None or self.empty_label is None:
            return

        items_list = list(items)
        self.table.setRowCount(len(items_list))

        for row, item in enumerate(items_list):
            game_id = int(item.get("game_id", 0))
            scenario_id = int(item.get("scenario_id", 0))
            created_at = str(item.get("created_at", ""))

            self.table.setItem(row, 0, QTableWidgetItem(str(game_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(scenario_id)))
            self.table.setItem(row, 2, QTableWidgetItem(created_at))

            actions_widget = QWidget(self.table)
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(6)

            download_btn = CButton(
                "Download Replay",
                "text",
                "primary",
                icon_name="mdi.download",
                parent=actions_widget,
            )
            download_btn.clicked.connect(
                lambda _checked=False, gid=game_id: self._handle_download_clicked(gid)
            )
            actions_layout.addWidget(download_btn)

            actions_layout.addStretch()
            self.table.setCellWidget(row, 3, actions_widget)

        self.badge_label.setText(str(len(items_list)))
        self.empty_label.setVisible(len(items_list) == 0)
        self.table.setVisible(len(items_list) > 0)

    # --------------------------------------------------------------------- #
    # Internal handlers
    # --------------------------------------------------------------------- #

    def _handle_refresh_clicked(self) -> None:
        if self._on_refresh:
            self._on_refresh()

    def _handle_download_clicked(self, game_id: int) -> None:
        if self._on_download_replay:
            self._on_download_replay(game_id)

