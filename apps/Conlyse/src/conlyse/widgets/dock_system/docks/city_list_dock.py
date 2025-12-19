"""City list dock for the MapPage right sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout


class CityListDock(QWidget):
    """Dock displaying a list of cities."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("city_list_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dock UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Cities")
        title.setObjectName("dock_title")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dock_separator")
        layout.addWidget(separator)
        
        # Scroll area for cities
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        
        # Dummy cities
        cities = [
            ("Berlin", "Germany", "3.5M", "85%"),
            ("Paris", "France", "2.2M", "78%"),
            ("London", "UK", "8.9M", "92%"),
            ("Moscow", "Russia", "12.5M", "88%"),
            ("Rome", "Italy", "2.8M", "81%"),
            ("Madrid", "Spain", "3.2M", "79%"),
            ("Warsaw", "Poland", "1.8M", "75%"),
        ]
        
        for name, owner, population, morale in cities:
            city_widget = self._create_city_item(name, owner, population, morale)
            content_layout.addWidget(city_widget)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _create_city_item(self, name: str, owner: str, population: str, morale: str) -> QWidget:
        """Create a city item widget."""
        widget = QWidget()
        widget.setObjectName("city_item")
        widget.setStyleSheet("""
            #city_item {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # City name
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(name_label)
        
        # Grid for details
        grid = QGridLayout()
        grid.setSpacing(4)
        
        # Owner
        owner_label = QLabel("Owner:")
        owner_label.setStyleSheet("color: #888; font-size: 11px;")
        owner_value = QLabel(owner)
        owner_value.setStyleSheet("font-size: 11px;")
        grid.addWidget(owner_label, 0, 0)
        grid.addWidget(owner_value, 0, 1)
        
        # Population
        pop_label = QLabel("Population:")
        pop_label.setStyleSheet("color: #888; font-size: 11px;")
        pop_value = QLabel(population)
        pop_value.setStyleSheet("font-size: 11px;")
        grid.addWidget(pop_label, 1, 0)
        grid.addWidget(pop_value, 1, 1)
        
        # Morale
        morale_label = QLabel("Morale:")
        morale_label.setStyleSheet("color: #888; font-size: 11px;")
        morale_value = QLabel(morale)
        morale_value.setStyleSheet("font-size: 11px;")
        grid.addWidget(morale_label, 2, 0)
        grid.addWidget(morale_value, 2, 1)
        
        layout.addLayout(grid)
        
        return widget
