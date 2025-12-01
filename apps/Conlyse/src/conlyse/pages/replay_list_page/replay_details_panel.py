# conlyse/pages/replay_list/replay_details_panel.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from conlyse.widgets.mui.button import CButton
from conlyse.widgets.mui.chip import CChip

if TYPE_CHECKING:
    from typing import Callable


class ReplayDetailsPanel(QWidget):
    """Panel for displaying detailed replay information"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.selected_replay = None
        self.selected_filepath: str | None = None

        # Callbacks
        self.on_analyze_callback: Callable | None = None
        self.on_delete_callback: Callable | None = None

        # UI Components
        self.details_title_label = None
        self.details_separator = None
        self.details_content = None
        self.details_content_layout = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the details panel UI"""
        self.setObjectName("replay_details_card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        self.details_title_label = QLabel("Replay Details")
        self.details_title_label.setObjectName("replay_details_card_title")
        layout.addWidget(self.details_title_label)

        # Separator
        self.details_separator = QFrame()
        self.details_separator.setObjectName("separator")
        self.details_separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.details_separator)

        # Scroll area for details content
        scroll = QScrollArea()
        scroll.setObjectName("replay_details_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.details_content = QWidget()
        self.details_content.setObjectName("replay_details_content")
        self.details_content_layout = QVBoxLayout(self.details_content)
        self.details_content_layout.setSpacing(20)
        scroll.setWidget(self.details_content)

        layout.addWidget(scroll)

    def set_callbacks(self, on_analyze=None, on_delete=None):
        """Set callback functions for actions"""
        self.on_analyze_callback = on_analyze
        self.on_delete_callback = on_delete

    def update_details(self, replay=None, filepath=None):
        """Update the details panel with replay info"""
        self.selected_replay = replay
        self.selected_filepath = filepath

        # Hide content during update
        self.details_content.setVisible(False)

        # Clear existing widgets
        self._clear_layout(self.details_content_layout)

        # Process events to ensure widgets are deleted
        QApplication.processEvents()

        if not self.selected_replay:
            self._show_empty_state()
            self.details_content.setVisible(True)
            return

        # Build content
        self._add_status_section()
        self._add_separator()
        self._add_info_grid()
        self._add_separator()
        self._add_file_path_section()
        self._add_separator()
        self._add_action_buttons()

        self.details_content_layout.addStretch()
        self.details_content.setVisible(True)

    def _show_empty_state(self):
        """Show empty state when no replay is selected"""
        empty_label = QLabel("Select a replay to view details")
        empty_label.setObjectName("replay_details_empty")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details_content_layout.addWidget(empty_label)
        self.details_content_layout.addStretch()

    def _add_status_section(self):
        """Add status section to details"""
        status_layout = QHBoxLayout()

        # Left side - title and date
        status_left = QVBoxLayout()
        status_left.setSpacing(4)

        status_title = QLabel("Game Status")
        status_title.setObjectName("replay_details_section_title")
        status_left.addWidget(status_title)

        status_date = QLabel("-1")  # TODO: Add actual date
        status_date.setObjectName("replay_details_section_subtitle")
        status_left.addWidget(status_date)

        status_layout.addLayout(status_left)
        status_layout.addStretch()

        # Right side - status badge
        is_running = True  # TODO: Get actual status
        status_badge = CChip(
            '▶ Running' if is_running else '⏹ Ended',
            variant="outlined",
            color="success" if is_running else "default"
        )
        status_layout.addWidget(status_badge)

        self.details_content_layout.addLayout(status_layout)

    def _add_info_grid(self):
        """Add info grid to details"""
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # Row 0
        self._add_info_field(grid, 0, 0, "📄 Game ID", "-1")
        self._add_info_field(grid, 0, 1, "🎮 Game Mode", "WW III")

        # Row 1
        self._add_info_field(grid, 1, 0, "🕐 Replay Length", "-1")
        self._add_info_field(grid, 1, 1, "📅 Game Day", "Day -1")

        # Row 2
        self._add_info_field(grid, 2, 0, "⚡ Game Speed", "-1")
        self._add_info_field(grid, 2, 1, "📍 Player Country", "-1")

        # Row 3
        self._add_info_field(grid, 3, 0, "💾 File Size", "-1")
        self._add_info_field(grid, 3, 1, "📅 Started", "-1")

        self.details_content_layout.addLayout(grid)

    def _add_file_path_section(self):
        """Add file path section to details"""
        path_label = QLabel("📁 File Path")
        path_label.setObjectName("replay_details_section_title")
        self.details_content_layout.addWidget(path_label)

        path_value = QLabel(self.selected_filepath if self.selected_filepath else "Unknown")
        path_value.setObjectName("replay_details_path")
        path_value.setWordWrap(True)
        self.details_content_layout.addWidget(path_value)

    def _add_action_buttons(self):
        """Add action buttons to details"""
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        # Analyze button (primary)
        analyze_btn = CButton("Analyze", "contained", "primary", "mdi.google-analytics")
        analyze_btn.clicked.connect(self._on_analyze_clicked)
        actions_layout.addWidget(analyze_btn)

        # Delete button (error/red)
        delete_btn = CButton("Delete", "contained", "error", "mdi.delete-forever")
        delete_btn.clicked.connect(self._on_delete_clicked)
        actions_layout.addWidget(delete_btn)

        self.details_content_layout.addLayout(actions_layout)

    def _add_separator(self):
        """Add a separator line to the details panel"""
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        self.details_content_layout.addWidget(separator)

    def _add_info_field(self, grid, row, col, label_text, value_text):
        """Add an info field to the grid"""
        container = QVBoxLayout()
        container.setSpacing(4)

        label = QLabel(label_text)
        label.setObjectName("replay_details_field_label")
        container.addWidget(label)

        value = QLabel(value_text)
        value.setObjectName("replay_details_field_value")
        container.addWidget(value)

        widget = QWidget()
        widget.setLayout(container)
        grid.addWidget(widget, row, col)

    def _clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _on_analyze_clicked(self):
        """Handle analyze button click"""
        if self.on_analyze_callback:
            self.on_analyze_callback()

    def _on_delete_clicked(self):
        """Handle delete button click"""
        if self.on_delete_callback:
            self.on_delete_callback()