"""Army information dock for the MapPage left sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout, QScrollArea


class ArmyInfoDock(QWidget):
    """Dock displaying information about a selected army."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("army_info_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dock UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Army Information")
        title.setObjectName("dock_title")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dock_separator")
        layout.addWidget(separator)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)
        
        # Content grid with dummy data
        grid = QGridLayout()
        grid.setSpacing(12)
        
        # Army Name
        self._add_info_row(grid, 0, "Army:", "1st Panzer Division")
        
        # Owner
        self._add_info_row(grid, 1, "Owner:", "Germany")
        
        # Location
        self._add_info_row(grid, 2, "Location:", "Berlin")
        
        # Strength
        self._add_info_row(grid, 3, "Strength:", "12,000 / 15,000")
        
        # Morale
        self._add_info_row(grid, 4, "Morale:", "92%")
        
        # Status
        self._add_info_row(grid, 5, "Status:", "Moving")
        
        # Units
        self._add_info_row(grid, 6, "Units:", "")
        
        content_layout.addLayout(grid)
        
        # Unit list
        units_label = QLabel("• 5x Main Battle Tank\n• 3x Infantry Fighting Vehicle\n• 2x Mobile Artillery\n• 1x Anti-Air Vehicle")
        units_label.setObjectName("dock_value")
        units_label.setStyleSheet("margin-left: 20px;")
        units_label.setWordWrap(True)
        content_layout.addWidget(units_label)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
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
