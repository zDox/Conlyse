"""Events dock for the MapPage right sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QScrollArea
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget


class EventsDock(QWidget):
    """Dock displaying game events."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("events_dock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dock UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Events")
        title.setObjectName("dock_title")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dock_separator")
        layout.addWidget(separator)
        
        # Scroll area for events
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        
        # Dummy events
        events = [
            ("Day 15, 08:30", "Declaration of War", "Germany declared war on France"),
            ("Day 14, 16:45", "Alliance Formed", "UK and France formed an alliance"),
            ("Day 14, 12:20", "Territory Captured", "Germany captured Paris"),
            ("Day 13, 09:15", "Research Complete", "Germany completed Tank Technology"),
            ("Day 12, 18:00", "Unit Built", "Germany built 5x Main Battle Tank"),
        ]
        
        for time, event_type, description in events:
            event_widget = self._create_event_item(time, event_type, description)
            content_layout.addWidget(event_widget)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _create_event_item(self, time: str, event_type: str, description: str) -> QWidget:
        """Create an event item widget."""
        widget = QWidget()
        widget.setObjectName("event_item")
        widget.setStyleSheet("""
            #event_item {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Time
        time_label = QLabel(time)
        time_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(time_label)
        
        # Event type
        type_label = QLabel(event_type)
        type_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(type_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(desc_label)
        
        return widget
