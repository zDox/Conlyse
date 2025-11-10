import sys
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QListWidget,
                             QListWidgetItem, QScrollArea, QFrame, QGridLayout)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon


class Replay:
    def __init__(self, id, game_id, length, game_mode, size_bytes, game_speed,
                 game_day, started_timestamp, file_path, status, player_country):
        self.id = id
        self.game_id = game_id
        self.length = length
        self.game_mode = game_mode
        self.size_bytes = size_bytes
        self.game_speed = game_speed
        self.game_day = game_day
        self.started_timestamp = started_timestamp
        self.file_path = file_path
        self.status = status
        self.player_country = player_country


# Mock data
MOCK_REPLAYS = [
    Replay('1', 'CON-4892341', '2h 34m', 'World War III', 45678901, '1x', 15,
           datetime(2025, 11, 8, 14, 30), '/replays/conflict_nations_20251108_143000.cnr',
           'Ended', 'United States'),
    Replay('2', 'CON-4892128', '5h 12m', 'Flashpoint', 89234567, '2x', 28,
           datetime(2025, 11, 7, 9, 15), '/replays/conflict_nations_20251107_091500.cnr',
           'Running', 'Russia'),
    Replay('3', 'CON-4891845', '1h 48m', 'Rising Tides', 34567890, '1x', 8,
           datetime(2025, 11, 6, 18, 45), '/replays/conflict_nations_20251106_184500.cnr',
           'Ended', 'China'),
    Replay('4', 'CON-4891234', '3h 22m', 'World War III', 67891234, '1.5x', 22,
           datetime(2025, 11, 5, 12, 0), '/replays/conflict_nations_20251105_120000.cnr',
           'Ended', 'United Kingdom'),
    Replay('5', 'CON-4890987', '4h 56m', 'Clash of Nations', 78901234, '2x', 35,
           datetime(2025, 11, 4, 16, 30), '/replays/conflict_nations_20251104_163000.cnr',
           'Running', 'Germany'),
    Replay('6', 'CON-4890654', '2h 15m', 'Flashpoint', 43218765, '1x', 12,
           datetime(2025, 11, 3, 21, 0), '/replays/conflict_nations_20251103_210000.cnr',
           'Ended', 'France'),
    Replay('7', 'CON-4890321', '6h 42m', 'World War III', 98765432, '1x', 45,
           datetime(2025, 11, 2, 8, 30), '/replays/conflict_nations_20251102_083000.cnr',
           'Ended', 'Japan'),
]


def format_bytes(bytes_val):
    if bytes_val == 0:
        return '0 Bytes'
    k = 1024
    sizes = ['Bytes', 'KB', 'MB', 'GB']
    i = int(len(bin(bytes_val)) - len(bin(k))) // 10
    if i >= len(sizes):
        i = len(sizes) - 1
    return f"{round(bytes_val / (k ** i), 2)} {sizes[i]}"


def format_date(date):
    return date.strftime('%b %d, %Y %I:%M %p')


class ReplayListItem(QWidget):
    def __init__(self, replay, is_dark=True, parent=None):
        super().__init__(parent)
        self.replay = replay
        self.is_dark = is_dark
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        # Top row with game ID and status
        top_layout = QHBoxLayout()

        text_color = "#E0E0E0" if self.is_dark else "#212121"

        self.game_id_label = QLabel(f"📄 {self.replay.game_id}")
        self.game_id_label.setStyleSheet(f"font-weight: 500; color: {text_color};")
        top_layout.addWidget(self.game_id_label)

        top_layout.addStretch()

        self.status_label = QLabel(f"{'▶' if self.replay.status == 'Running' else '⏹'} {self.replay.status}")
        self.update_status_style()
        top_layout.addWidget(self.status_label)

        layout.addLayout(top_layout)

        # Game mode
        muted_color = "#9E9E9E" if self.is_dark else "#757575"
        self.mode_label = QLabel(self.replay.game_mode)
        self.mode_label.setStyleSheet(f"color: {muted_color}; font-size: 13px; margin-top: 4px;")
        layout.addWidget(self.mode_label)

        # Bottom info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)

        self.length_label = QLabel(f"🕐 {self.replay.length}")
        self.length_label.setStyleSheet(f"color: {muted_color}; font-size: 12px;")
        info_layout.addWidget(self.length_label)

        self.day_label = QLabel(f"📅 Day {self.replay.game_day}")
        self.day_label.setStyleSheet(f"color: {muted_color}; font-size: 12px;")
        info_layout.addWidget(self.day_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

    def update_status_style(self):
        if self.replay.status == 'Running':
            self.status_label.setStyleSheet("""
                background-color: #1976D2;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 500;
            """)
        else:
            bg_color = "#424242" if self.is_dark else "#E0E0E0"
            text_color = "#E0E0E0" if self.is_dark else "#424242"
            self.status_label.setStyleSheet(f"""
                background-color: {bg_color};
                color: {text_color};
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 500;
            """)

    def update_theme(self, is_dark):
        self.is_dark = is_dark
        text_color = "#E0E0E0" if is_dark else "#212121"
        muted_color = "#9E9E9E" if is_dark else "#757575"

        self.game_id_label.setStyleSheet(f"font-weight: 500; color: {text_color};")
        self.mode_label.setStyleSheet(f"color: {muted_color}; font-size: 13px; margin-top: 4px;")
        self.length_label.setStyleSheet(f"color: {muted_color}; font-size: 12px;")
        self.day_label.setStyleSheet(f"color: {muted_color}; font-size: 12px;")
        self.update_status_style()


class ReplayAnalyser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_replay = MOCK_REPLAYS[0]
        self.is_dark_mode = True
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Conflict of Nations Replay Analyser")
        self.setMinimumSize(1400, 800)

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
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
        self.app.event_handler.registerKey("theme_toggle", self.theme_toggle)
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

        # Apply initial theme
        self.apply_theme()

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
            widget = ReplayListItem(replay, self.is_dark_mode)
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
        scroll.setStyleSheet("""
            QScrollArea { 
                background-color: transparent; 
                border: none; 
            }
            QScrollArea > QWidget > QWidget { 
                background-color: transparent; 
            }
        """)

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

        export_btn = QPushButton("📄 Export Data")
        export_btn.setObjectName("secondary")
        actions_layout.addWidget(export_btn)

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

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

        # Update theme toggle button text
        if self.is_dark_mode:
            self.theme_toggle.setText("☀️ Light Mode")
        else:
            self.theme_toggle.setText("🌙 Dark Mode")

        # Update all list items
        for i in range(self.replay_list.count()):
            item = self.replay_list.item(i)
            widget = self.replay_list.itemWidget(item)
            if isinstance(widget, ReplayListItem):
                widget.update_theme(self.is_dark_mode)

        # Update details
        self.update_details()

    def apply_theme(self):
        if self.is_dark_mode:
            # Dark theme
            bg_color = "#121212"
            card_color = "#1E1E1E"
            text_color = "#E0E0E0"
            muted_color = "#9E9E9E"
            separator_color = "#2C2C2C"
            hover_color = "#2C2C2C"
            badge_bg = "#424242"
            badge_text = "#E0E0E0"
            code_bg = "#2C2C2C"
            scrollbar_bg = "#1E1E1E"
            scrollbar_handle = "#424242"
            scrollbar_hover = "#616161"
        else:
            # Light theme
            bg_color = "#FAFAFA"
            card_color = "#FFFFFF"
            text_color = "#212121"
            muted_color = "#757575"
            separator_color = "#E0E0E0"
            hover_color = "#F5F5F5"
            badge_bg = "#E0E0E0"
            badge_text = "#424242"
            code_bg = "#F5F5F5"
            scrollbar_bg = "#F5F5F5"
            scrollbar_handle = "#BDBDBD"
            scrollbar_hover = "#9E9E9E"

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton#primary {{
                background-color: #1976D2;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 14px;
            }}
            QPushButton#primary:hover {{
                background-color: #1565C0;
            }}
            QPushButton#secondary {{
                background-color: transparent;
                border: 1px solid {separator_color};
                color: {text_color};
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 14px;
            }}
            QPushButton#secondary:hover {{
                background-color: {hover_color};
            }}
            QPushButton#themeToggle {{
                background-color: {card_color};
                color: {text_color};
                border: 1px solid {separator_color};
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 13px;
            }}
            QPushButton#themeToggle:hover {{
                background-color: {hover_color};
            }}
            QListWidget {{
                background-color: {card_color};
                border: none;
                border-radius: 8px;
                padding: 0px;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {separator_color};
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background-color: {hover_color};
            }}
            QListWidget::item:hover {{
                background-color: {hover_color};
            }}
            QScrollBar:vertical {{
                background-color: {scrollbar_bg};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {scrollbar_handle};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {scrollbar_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                background-color: {scrollbar_bg};
                height: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {scrollbar_handle};
                border-radius: 6px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {scrollbar_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
            QFrame#card {{
                background-color: {card_color};
                border-radius: 8px;
                padding: 20px;
            }}
            QLabel#header {{
                font-size: 32px;
                font-weight: 300;
                color: {text_color};
                margin-bottom: 4px;
            }}
            QLabel#subheader {{
                font-size: 14px;
                color: {muted_color};
                margin-bottom: 24px;
            }}
            QLabel#cardTitle {{
                font-size: 20px;
                font-weight: 500;
                color: {text_color};
                margin-bottom: 12px;
            }}
            QLabel#badge {{
                background-color: {badge_bg};
                color: {badge_text};
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QLabel#statusTitle {{
                font-size: 18px;
                font-weight: 500;
                color: {text_color};
            }}
            QLabel#statusBadge {{
                padding: 8px 16px;
                border-radius: 16px;
                font-size: 14px;
                font-weight: 500;
            }}
            QLabel#statusBadge[status="running"] {{
                background-color: #1976D2;
                color: white;
            }}
            QLabel#statusBadge[status="ended"] {{
                background-color: {badge_bg};
                color: {badge_text};
            }}
            QLabel#sectionLabel {{
                color: {muted_color};
                font-size: 13px;
                margin-bottom: 4px;
            }}
            QLabel#value {{
                color: {text_color};
                font-size: 14px;
                margin-left: 24px;
            }}
            QFrame#separator {{
                background-color: {separator_color};
                max-height: 1px;
                min-height: 1px;
            }}
            QLabel#codeBlock {{
                background-color: {code_bg};
                color: {text_color};
                padding: 12px;
                border-radius: 4px;
                font-family: monospace;
                margin-left: 24px;
            }}
        """)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set application font
    font = QFont("Roboto", 10)
    app.setFont(font)

    window = ReplayAnalyser()
    window.show()

    sys.exit(app.exec())