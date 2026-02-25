"""Army list dock for the MapPage right sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout

from conlyse.widgets.dock_system.docks.dock import Dock


class ArmyListDock(Dock):
    """Dock displaying a list of armies."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("army_list_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dock UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Armies")
        title.setObjectName("dock_title")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dock_separator")
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
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Army name
        name_label = QLabel(name)
        name_label.setObjectName("dock_item_title")
        layout.addWidget(name_label)
        
        # Grid for details
        grid = QGridLayout()
        grid.setSpacing(4)
        
        # Owner
        owner_label = QLabel("Owner:")
        owner_label.setObjectName("dock_item_meta")
        owner_value = QLabel(owner)
        owner_value.setObjectName("dock_item_value")
        grid.addWidget(owner_label, 0, 0)
        grid.addWidget(owner_value, 0, 1)
        
        # Location
        loc_label = QLabel("Location:")
        loc_label.setObjectName("dock_item_meta")
        loc_value = QLabel(location)
        loc_value.setObjectName("dock_item_value")
        grid.addWidget(loc_label, 1, 0)
        grid.addWidget(loc_value, 1, 1)
        
        # Strength
        strength_label = QLabel("Strength:")
        strength_label.setObjectName("dock_item_meta")
        strength_value = QLabel(strength)
        strength_value.setObjectName("dock_item_value")
        grid.addWidget(strength_label, 2, 0)
        grid.addWidget(strength_value, 2, 1)
        
        # Morale
        morale_label = QLabel("Morale:")
        morale_label.setObjectName("dock_item_meta")
        morale_value = QLabel(morale)
        morale_value.setObjectName("dock_item_value")
        grid.addWidget(morale_label, 3, 0)
        grid.addWidget(morale_value, 3, 1)
        
        layout.addLayout(grid)
        
        return widget
