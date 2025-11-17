from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget
from conflict_interface.replay.replay import Replay

from conlyse.logger import get_logger
from conlyse.managers.style_manager import Theme
from conlyse.pages.page import Page

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()

class ReplayListItem(QWidget):
    def __init__(self, replay_data, parent=None):
        super().__init__(parent)
        self.day_label = None
        self.length_label = None
        self.mode_label = None
        self.status_label = None
        self.game_id_label = None
        self.replay_data: dict = replay_data
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        # Top row with game ID and status
        top_layout = QHBoxLayout()

        self.game_id_label = QLabel(f"📄 {self.replay_data.get('game_id', 'Unknown')}")
        self.game_id_label.setObjectName("listItemTitle")
        top_layout.addWidget(self.game_id_label)

        top_layout.addStretch()

        self.status_label = QLabel(f"{'▶' if self.replay_data.get('status', 'Running') == 'Running' else '⏹'} {self.replay_data.get('status', 'Running')}")
        self.status_label.setObjectName("listItemStatus")
        if self.replay_data.get('status', 'Running') == 'Running':
            self.status_label.setProperty("status", "running")
        else:
            self.status_label.setProperty("status", "ended")
        top_layout.addWidget(self.status_label)

        layout.addLayout(top_layout)

        # Game mode
        self.mode_label = QLabel(self.replay_data.get('game_mode', 'Unknown'))
        self.mode_label.setObjectName("listItemMode")
        layout.addWidget(self.mode_label)

        # Bottom info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)

        self.length_label = QLabel(f"🕐 {self.replay_data.get('length', '-1')}")
        self.length_label.setObjectName("listItemInfo")
        info_layout.addWidget(self.length_label)

        self.day_label = QLabel(f"📅 Day {self.replay_data.get('day', '-1')}")
        self.day_label.setObjectName("listItemInfo")
        info_layout.addWidget(self.day_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)


class ReplayListPage(Page):
    """Widget version of ReplayAnalyser for use in QStackedWidget"""

    HEADER = False

    def __init__(self, app, parent=None):
        super().__init__(parent)

        self.details_content_layout = None
        self.details_content = None
        self.details_separator = None
        self.details_title_label = None
        self.details_layout = None
        self.details_frame = None
        self.list_frame = None
        self.list_separator = None
        self.badge_label = None
        self.replay_list = None
        self.open_replay_btn = None
        self.list_title_label = None
        self.subheader_label = None
        self.header_label = None
        self.app: App = app
        self.selected_replay: Replay | None = None

        self.selected_filepath: str | None = None

        self.theme_toggle = None


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

        self.badge_label = QLabel(str(len(self.app.replay_manager.get_replays().values())))
        self.badge_label.setObjectName("badge")
        self.badge_label.setMaximumWidth(40)
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.badge_label)
        header_layout.addStretch()

        # Open button in top right
        self.open_replay_btn = QPushButton("▶ Open")
        self.open_replay_btn.setObjectName("primary")
        self.open_replay_btn.setMaximumWidth(100)
        self.open_replay_btn.clicked.connect(self.on_open_replay)
        header_layout.addWidget(self.open_replay_btn)

        list_layout.addLayout(header_layout)

        # Separator
        self.list_separator = QFrame()
        self.list_separator.setObjectName("separator")
        list_layout.addWidget(self.list_separator)

        # List
        self.replay_list = QListWidget()
        self.replay_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.replay_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        for replay in self.app.replay_manager.get_replays().values():
            replay_data = {} # TODO
            item = QListWidgetItem(self.replay_list)
            item.setSizeHint(QSize(340, 90))
            widget = ReplayListItem(replay_data)
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

        # Status section
        status_layout = QHBoxLayout()

        status_left = QVBoxLayout()
        status_title = QLabel("Game Status")
        status_title.setObjectName("statusTitle")
        status_left.addWidget(status_title)

        status_date = QLabel("-1")
        status_date.setObjectName("sectionLabel")
        status_left.addWidget(status_date)
        status_layout.addLayout(status_left)

        status_layout.addStretch()

        status_badge = QLabel(f"{'▶' if True else '⏹'}") # TODO
        status_badge.setObjectName("statusBadge")
        if True: # TODO
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
        self.add_info_field(grid, 0, 0, "📄 Game ID", "-1")
        self.add_info_field(grid, 0, 1, "🎮 Game Mode", "WW III")

        # Row 1
        self.add_info_field(grid, 1, 0, "🕐 Replay Length", "-1")
        self.add_info_field(grid, 1, 1, "📅 Game Day", f"Day {-1}")

        # Row 2
        self.add_info_field(grid, 2, 0, "⚡ Game Speed", "-1")
        self.add_info_field(grid, 2, 1, "📍 Player Country", "-1")

        # Row 3
        self.add_info_field(grid, 3, 0, "💾 File Size", "-1")
        self.add_info_field(grid, 3, 1, "📅 Started", "-1")

        self.details_content_layout.addLayout(grid)

        self.add_separator()

        # File path
        path_label = QLabel("📁 File Path")
        path_label.setObjectName("sectionLabel")
        self.details_content_layout.addWidget(path_label)

        path_value = QLabel(self.selected_filepath if self.selected_filepath else "Unknown")
        path_value.setObjectName("codeBlock")
        path_value.setWordWrap(True)
        self.details_content_layout.addWidget(path_value)

        self.add_separator()

        # Actions
        actions_layout = QHBoxLayout()

        open_btn = QPushButton("▶ Analyze Replay")
        open_btn.setObjectName("primary")
        actions_layout.addWidget(open_btn)

        delete_btn = QPushButton("Delete Replay")
        delete_btn.setObjectName("secondary")
        actions_layout.addWidget(delete_btn)

        self.details_content_layout.addLayout(actions_layout)
        self.details_content_layout.addStretch()

        # rebuild replay list to ensure it's up to date
        self.replay_list.clear()
        for replay in self.app.replay_manager.get_replays().values():
            replay_data = {} # TODO
            item = QListWidgetItem(self.replay_list)
            item.setSizeHint(QSize(340, 90))
            widget = ReplayListItem(replay_data)
            self.replay_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, replay)

        

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

    def on_replay_selected(self, current):
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

    def on_open_replay(self):
        default_path = self.app.config_manager.get("file.default_open_path", "")
        replay_file_extension = self.app.config_manager.get("file.replay_file_extension", ".db")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Replay Database",
            default_path,  # Starting directory (empty = last used directory)
            f"Replay Files (*{replay_file_extension});;All Files (*.*)"
        )

        if not file_path:
            return

        # File was selected
        logger.debug(f"Selected replay file: {file_path}")
        success = self.app.replay_manager.open_new_replay(file_path)
        if success:
            # Refresh the page to show the new replay
            self.selected_replay = self.app.replay_manager.get_replays()[file_path]
            self.selected_filepath = file_path
            self.update_details()
        else:
            # summon pyqt message box to show error

            msg = QMessageBox()
            msg.setObjectName("errorMessageBox")
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Error Opening Replay")
            msg.setText("Failed to open the selected replay file. It may be corrupted or invalid.")
            msg.exec()



    def clean_up(self):
        self.clear_layout(self.layout())

    def update(self):
        pass

    def setup(self, context):
        self.setup_ui()

