from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QListWidget,
                             QListWidgetItem, QScrollArea, QFrame, QGridLayout)
from PyQt6.QtCore import Qt, QSize
from conlyse.utils.formating import format_bytes, format_date
from conlyse.pages.page import Page
from conlyse.managers.style_manager import Theme

# RM ----------------------------
from conlyse.utils.mock_replay import *
# -------------------------------

if TYPE_CHECKING:
    from conlyse.app import App

class ReplayListItem(QWidget):
    def __init__(self, replay, parent=None):
        super().__init__(parent)
        self.replay = replay
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        # Top row with game ID and status
        top_layout = QHBoxLayout()

        self.game_id_label = QLabel(f"📄 {self.replay.game_id}")
        self.game_id_label.setObjectName("listItemTitle")
        top_layout.addWidget(self.game_id_label)

        top_layout.addStretch()

        self.status_label = QLabel(f"{'▶' if self.replay.status == 'Running' else '⏹'} {self.replay.status}")
        self.status_label.setObjectName("listItemStatus")
        if self.replay.status == 'Running':
            self.status_label.setProperty("status", "running")
        else:
            self.status_label.setProperty("status", "ended")
        top_layout.addWidget(self.status_label)

        layout.addLayout(top_layout)

        # Game mode
        self.mode_label = QLabel(self.replay.game_mode)
        self.mode_label.setObjectName("listItemMode")
        layout.addWidget(self.mode_label)

        # Bottom info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)

        self.length_label = QLabel(f"🕐 {self.replay.length}")
        self.length_label.setObjectName("listItemInfo")
        info_layout.addWidget(self.length_label)

        self.day_label = QLabel(f"📅 Day {self.replay.game_day}")
        self.day_label.setObjectName("listItemInfo")
        info_layout.addWidget(self.day_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)


class ReplayListPage(Page):
    """Widget version of ReplayAnalyser for use in QStackedWidget"""

    HEADER = False

    def __init__(self, app, parent=None):
        super().__init__(parent)

        self.app: App = app
        self.selected_replay = MOCK_REPLAYS[0]

    def setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)

        # Header with theme toggle
        header_layout = QHBoxLayout()

        header_left = QVBoxLayout()
        self.header_label = QLabel("Conflict of Nations Replay Analyser")
        self.header_label.setObjectName("header")
        header_left.addWidget(self.header_label)

        self.subheader_label = QLabel("View and analyze your recorded game replays")
        self.subheader_label.setObjectName("subheader")
        header_left.addWidget(self.subheader_label)

        header_layout.addLayout(header_left)
        header_layout.addStretch()

        # Theme toggle button
        self.theme_toggle = QPushButton("☀️ Light Mode")
        self.theme_toggle.setObjectName("themeToggle")
        self.theme_toggle.setMaximumWidth(140)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_toggle, alignment=Qt.AlignmentFlag.AlignTop)

        main_layout.addLayout(header_layout)

        # Content area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)

        # Left side - Replay list
        self.setup_replay_list(content_layout)

        # Right side - Details
        self.setup_details_panel(content_layout)

        main_layout.addLayout(content_layout)

    def setup_replay_list(self, parent_layout):
        self.list_frame = QFrame()
        self.list_frame.setObjectName("card")
        self.list_frame.setMinimumWidth(380)
        self.list_frame.setMaximumWidth(420)
        list_layout = QVBoxLayout(self.list_frame)
        list_layout.setContentsMargins(20, 20, 20, 20)
        list_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        self.list_title_label = QLabel("Recorded Replays")
        self.list_title_label.setObjectName("cardTitle")
        header_layout.addWidget(self.list_title_label)

        self.badge_label = QLabel(str(len(MOCK_REPLAYS)))
        self.badge_label.setObjectName("badge")
        self.badge_label.setMaximumWidth(40)
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.badge_label)
        header_layout.addStretch()

        list_layout.addLayout(header_layout)

        # Separator
        self.list_separator = QFrame()
        self.list_separator.setObjectName("separator")
        list_layout.addWidget(self.list_separator)

        # List
        self.replay_list = QListWidget()
        self.replay_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.replay_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        for replay in MOCK_REPLAYS:
            item = QListWidgetItem(self.replay_list)
            item.setSizeHint(QSize(340, 90))
            widget = ReplayListItem(replay)
            self.replay_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, replay)

        self.replay_list.setCurrentRow(0)
        self.replay_list.currentItemChanged.connect(self.on_replay_selected)

        list_layout.addWidget(self.replay_list)
        parent_layout.addWidget(self.list_frame)

    def setup_details_panel(self, parent_layout):
        self.details_frame = QFrame()
        self.details_frame.setObjectName("card")
        self.details_layout = QVBoxLayout(self.details_frame)
        self.details_layout.setContentsMargins(20, 20, 20, 20)
        self.details_layout.setSpacing(16)

        # Title
        self.details_title_label = QLabel("Replay Details")
        self.details_title_label.setObjectName("cardTitle")
        self.details_layout.addWidget(self.details_title_label)

        # Separator
        self.details_separator = QFrame()
        self.details_separator.setObjectName("separator")
        self.details_layout.addWidget(self.details_separator)

        # Scroll area for details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("detailsScrollArea")

        self.details_content = QWidget()
        self.details_content_layout = QVBoxLayout(self.details_content)
        self.details_content_layout.setSpacing(20)
        scroll.setWidget(self.details_content)

        self.details_layout.addWidget(scroll)
        parent_layout.addWidget(self.details_frame)

        self.update_details()

    def update_details(self):
        # Completely clear and delete all widgets
        while self.details_content_layout.count():
            item = self.details_content_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

        # Force process events to ensure widgets are deleted
        QApplication.processEvents()

        if not self.selected_replay:
            return

        r = self.selected_replay

        # Status section
        status_layout = QHBoxLayout()

        status_left = QVBoxLayout()
        status_title = QLabel("Game Status")
        status_title.setObjectName("statusTitle")
        status_left.addWidget(status_title)

        status_date = QLabel(format_date(r.started_timestamp))
        status_date.setObjectName("sectionLabel")
        status_left.addWidget(status_date)
        status_layout.addLayout(status_left)

        status_layout.addStretch()

        status_badge = QLabel(f"{'▶' if r.status == 'Running' else '⏹'} {r.status}")
        status_badge.setObjectName("statusBadge")
        if r.status == 'Running':
            status_badge.setProperty("status", "running")
        else:
            status_badge.setProperty("status", "ended")
        status_layout.addWidget(status_badge)

        self.details_content_layout.addLayout(status_layout)

        self.add_separator()

        # Info grid
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # Row 0
        self.add_info_field(grid, 0, 0, "📄 Game ID", r.game_id)
        self.add_info_field(grid, 0, 1, "🎮 Game Mode", r.game_mode)

        # Row 1
        self.add_info_field(grid, 1, 0, "🕐 Replay Length", r.length)
        self.add_info_field(grid, 1, 1, "📅 Game Day", f"Day {r.game_day}")

        # Row 2
        self.add_info_field(grid, 2, 0, "⚡ Game Speed", r.game_speed)
        self.add_info_field(grid, 2, 1, "📍 Player Country", r.player_country)

        # Row 3
        self.add_info_field(grid, 3, 0, "💾 File Size", format_bytes(r.size_bytes))
        self.add_info_field(grid, 3, 1, "📅 Started", format_date(r.started_timestamp))

        self.details_content_layout.addLayout(grid)

        self.add_separator()

        # File path
        path_label = QLabel("📁 File Path")
        path_label.setObjectName("sectionLabel")
        self.details_content_layout.addWidget(path_label)

        path_value = QLabel(r.file_path)
        path_value.setObjectName("codeBlock")
        path_value.setWordWrap(True)
        self.details_content_layout.addWidget(path_value)

        self.add_separator()

        # Actions
        actions_layout = QHBoxLayout()

        open_btn = QPushButton("▶ Open Replay")
        open_btn.setObjectName("primary")
        actions_layout.addWidget(open_btn)

        delete_btn = QPushButton("Delete Replay")
        delete_btn.setObjectName("secondary")
        actions_layout.addWidget(delete_btn)

        self.details_content_layout.addLayout(actions_layout)
        self.details_content_layout.addStretch()

    def add_separator(self):
        separator = QFrame()
        separator.setObjectName("separator")
        self.details_content_layout.addWidget(separator)

    def add_info_field(self, grid, row, col, label_text, value_text):
        container = QVBoxLayout()
        container.setSpacing(0)

        label = QLabel(label_text)
        label.setObjectName("sectionLabel")
        container.addWidget(label)

        value = QLabel(value_text)
        value.setObjectName("value")
        container.addWidget(value)

        widget = QWidget()
        widget.setLayout(container)
        grid.addWidget(widget, row, col)

    def clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def on_replay_selected(self, current, previous):
        if current:
            self.selected_replay = current.data(Qt.ItemDataRole.UserRole)
            self.update_details()

    @pyqtSlot()
    def toggle_theme(self):
        self.app.style_manager.toggle_theme()

        # Update theme toggle button text

        if self.app.style_manager.get_current_theme() == Theme.DARK:

            self.theme_toggle.setText("☀️ Light Mode")
        else:
            self.theme_toggle.setText("🌙 Dark Mode")

        # Update details to refresh any dynamic content
        self.update_details()

    def clean_up(self):
        self.clear_layout()

    def update(self):
        pass

    def setup(self, context):
        self.setup_ui()
