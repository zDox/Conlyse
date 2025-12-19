"""Province information dock for the MapPage left sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout


class ProvinceInfoDock(QWidget):
    """Dock displaying information about a selected province."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("province_info_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dock UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Province Information")
        title.setObjectName("dock_title")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dock_separator")
        layout.addWidget(separator)
        
        # Content grid with dummy data
        grid = QGridLayout()
        grid.setSpacing(12)
        
        # Province Name
        self._add_info_row(grid, 0, "Province:", "Berlin")
        
        # Owner
        self._add_info_row(grid, 1, "Owner:", "Germany")
        
        # Population
        self._add_info_row(grid, 2, "Population:", "3,500,000")
        
        # Morale
        self._add_info_row(grid, 3, "Morale:", "85%")
        
        # Terrain
        self._add_info_row(grid, 4, "Terrain:", "Urban")
        
        # Resources
        self._add_info_row(grid, 5, "Resources:", "Electronics, Machinery")
        
        # Infrastructure
        self._add_info_row(grid, 6, "Infrastructure:", "Level 5")
        
        layout.addLayout(grid)
        layout.addStretch()
    
    def _add_info_row(self, grid: QGridLayout, row: int, label: str, value: str):
        """Add an information row to the grid."""
        label_widget = QLabel(label)
        label_widget.setObjectName("dock_label")
        label_widget.setStyleSheet("color: #888;")
        
        value_widget = QLabel(value)
        value_widget.setObjectName("dock_value")
        value_widget.setStyleSheet("font-weight: 500;")
        
        grid.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(value_widget, row, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
