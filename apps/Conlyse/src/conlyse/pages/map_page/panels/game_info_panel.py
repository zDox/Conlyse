"""Game information panel for the MapPage left sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout


class GameInfoPanel(QWidget):
    """Panel displaying general game information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("game_info_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Game Information")
        title.setObjectName("panel_title")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("panel_separator")
        layout.addWidget(separator)
        
        # Content grid with dummy data
        grid = QGridLayout()
        grid.setSpacing(12)
        
        # Game ID
        self._add_info_row(grid, 0, "Game ID:", "123456")
        
        # Game Mode
        self._add_info_row(grid, 1, "Game Mode:", "WW III")
        
        # Game Day
        self._add_info_row(grid, 2, "Current Day:", "Day 15")
        
        # Game Speed
        self._add_info_row(grid, 3, "Game Speed:", "1x")
        
        # Players
        self._add_info_row(grid, 4, "Players:", "24/32")
        
        # Status
        self._add_info_row(grid, 5, "Status:", "Running")
        
        layout.addLayout(grid)
        layout.addStretch()
    
    def _add_info_row(self, grid: QGridLayout, row: int, label: str, value: str):
        """Add an information row to the grid."""
        label_widget = QLabel(label)
        label_widget.setObjectName("panel_label")
        label_widget.setStyleSheet("color: #888;")
        
        value_widget = QLabel(value)
        value_widget.setObjectName("panel_value")
        value_widget.setStyleSheet("font-weight: 500;")
        
        grid.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(value_widget, row, 1, Qt.AlignmentFlag.AlignLeft)
