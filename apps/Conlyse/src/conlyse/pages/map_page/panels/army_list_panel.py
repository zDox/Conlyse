"""Army list panel for the MapPage right sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout


class ArmyListPanel(QWidget):
    """Panel displaying a list of armies."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("army_list_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Armies")
        title.setObjectName("panel_title")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("panel_separator")
        layout.addWidget(separator)
        
        # Scroll area for armies
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        
        # Dummy armies
        armies = [
            ("1st Panzer Division", "Germany", "Berlin", "12K/15K", "92%"),
            ("2nd Infantry Corps", "Germany", "Munich", "18K/20K", "88%"),
            ("Royal Guards", "UK", "London", "10K/10K", "95%"),
            ("French Foreign Legion", "France", "Paris", "8K/12K", "82%"),
            ("Red Army Battalion", "Russia", "Moscow", "25K/30K", "90%"),
        ]
        
        for name, owner, location, strength, morale in armies:
            army_widget = self._create_army_item(name, owner, location, strength, morale)
            content_layout.addWidget(army_widget)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _create_army_item(self, name: str, owner: str, location: str, strength: str, morale: str) -> QWidget:
        """Create an army item widget."""
        widget = QWidget()
        widget.setObjectName("army_item")
        widget.setStyleSheet("""
            #army_item {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Army name
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
        
        # Location
        loc_label = QLabel("Location:")
        loc_label.setStyleSheet("color: #888; font-size: 11px;")
        loc_value = QLabel(location)
        loc_value.setStyleSheet("font-size: 11px;")
        grid.addWidget(loc_label, 1, 0)
        grid.addWidget(loc_value, 1, 1)
        
        # Strength
        strength_label = QLabel("Strength:")
        strength_label.setStyleSheet("color: #888; font-size: 11px;")
        strength_value = QLabel(strength)
        strength_value.setStyleSheet("font-size: 11px;")
        grid.addWidget(strength_label, 2, 0)
        grid.addWidget(strength_value, 2, 1)
        
        # Morale
        morale_label = QLabel("Morale:")
        morale_label.setStyleSheet("color: #888; font-size: 11px;")
        morale_value = QLabel(morale)
        morale_value.setStyleSheet("font-size: 11px;")
        grid.addWidget(morale_label, 3, 0)
        grid.addWidget(morale_value, 3, 1)
        
        layout.addLayout(grid)
        
        return widget
