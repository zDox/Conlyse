# conlyse/pages/replay_list/replay_list_item.py
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from conlyse.widgets.mui.chip import CChip
from conlyse.widgets.mui.label import CLabel


class ReplayListItem(QWidget):
    """Custom widget for displaying replay information in a list"""

    def __init__(self, replay_data, parent=None):
        super().__init__(parent)
        self.replay_data: dict = replay_data

        # Widget references
        self.game_id_label = None
        self.status_chip = None
        self.mode_label = None
        self.length_label = None
        self.day_label = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the list item UI"""
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Top row with game ID and status
        self._setup_top_row(layout)

        # Game mode
        self.mode_label = CLabel(self.replay_data.get('game_mode', 'Unknown'))
        self.mode_label.setObjectName("replay_list_item_mode")
        layout.addWidget(self.mode_label)

        # Bottom info row
        self._setup_info_row(layout)

    def _setup_top_row(self, parent_layout):
        """Setup the top row with game ID and status"""
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        self.game_id_label = CLabel(
            f"{self.replay_data.get('game_id', 'Unknown')}",
            "mdi.gamepad-square",
            "primary"
        )
        self.game_id_label.setObjectName("replay_list_item_title")
        top_layout.addWidget(self.game_id_label)

        top_layout.addStretch()

        self.status_chip = CChip("Unknown", "outlined")
        self.update_status_chip()
        top_layout.addWidget(self.status_chip)

        parent_layout.addLayout(top_layout)

    def _setup_info_row(self, parent_layout):
        """Setup the bottom info row"""
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)

        self.length_label = CLabel(
            f"{self.replay_data.get('length', '-1')}",
            "ri.time-fill",
            "primary"
        )
        self.length_label.setObjectName("replay_list_item_info")
        info_layout.addWidget(self.length_label)

        self.day_label = CLabel(
            f"Day {self.replay_data.get('day', '-1')}",
            "ei.calendar",
            "primary"
        )
        self.day_label.setObjectName("replay_list_item_info")
        info_layout.addWidget(self.day_label)

        info_layout.addStretch()
        parent_layout.addLayout(info_layout)

    def update_status_chip(self):
        """Update the status chip text and style"""
        status_text = self.replay_data.get('status', 'Running')
        if status_text == 'Running':
            self.status_chip.set_text('▶ Running')
            self.status_chip.set_color("success")
        else:
            self.status_chip.set_text('⏹ Ended')
            self.status_chip.set_color("info")
        self.status_chip.refresh()