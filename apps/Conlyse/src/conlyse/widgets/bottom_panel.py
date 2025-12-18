"""
Bottom panel widget for ReplayPage.
Can display different content like TimelineControls.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy

if TYPE_CHECKING:
    pass


class BottomPanel(QWidget):
    """
    A bottom panel widget that can display different content.
    Positioned at the bottom of the ReplayPage, with toggle buttons in the lower left.
    """
    
    def __init__(self, parent=None, default_height: int = 150):
        """
        Initialize the bottom panel.
        
        Args:
            parent: Parent widget
            default_height: Default height of the panel when visible
        """
        super().__init__(parent)
        self.default_height = default_height
        self.active_content = None
        self.content_widgets = {}  # panel_name -> widget
        self.toggle_buttons = {}  # panel_name -> button
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("bottom_panel")
        
        # Main layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Left toggle button area
        self.button_strip = QWidget(self)
        self.button_strip.setObjectName("bottom_panel_button_strip")
        self.button_strip.setFixedWidth(40)
        self.button_strip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        
        self.button_layout = QHBoxLayout(self.button_strip)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        self.button_layout.addStretch()
        
        # Content container
        self.content_container = QWidget(self)
        self.content_container.setObjectName("bottom_panel_content_container")
        self.content_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self.main_layout.addWidget(self.button_strip)
        self.main_layout.addWidget(self.content_container)
        
        # Start hidden
        self.hide()
    
    def add_content(self, name: str, label: str, widget: QWidget):
        """
        Add a content widget that can be displayed in the bottom panel.
        
        Args:
            name: Unique identifier for the content
            label: Text to display on the button
            widget: The widget to show when content is selected
        """
        # Create button
        button = QPushButton(label, self.button_strip)
        button.setObjectName("bottom_panel_button")
        button.setFixedWidth(40)
        button.setCheckable(True)
        button.clicked.connect(lambda checked: self.toggle_content(name))
        
        # Insert button before the stretch
        self.button_layout.insertWidget(self.button_layout.count() - 1, button)
        
        # Store content
        widget.setParent(self.content_container)
        widget.hide()
        self.content_widgets[name] = widget
        self.toggle_buttons[name] = button
    
    def toggle_content(self, name: str):
        """
        Toggle a content widget open or closed.
        
        Args:
            name: Name of the content to toggle
        """
        if name not in self.content_widgets:
            return
        
        button = self.toggle_buttons[name]
        widget = self.content_widgets[name]
        
        # If clicking the currently active content, close it
        if self.active_content == name:
            self.close_content()
        else:
            # Close currently active content if any
            if self.active_content:
                self.close_content()
            # Open the new content
            self.open_content(name)
    
    def open_content(self, name: str):
        """
        Open a specific content widget.
        
        Args:
            name: Name of the content to open
        """
        if name not in self.content_widgets:
            return
        
        # Close any currently active content first
        if self.active_content:
            self.close_content()
        
        button = self.toggle_buttons[name]
        widget = self.content_widgets[name]
        
        # Update button state
        button.setChecked(True)
        
        # Clear content layout and add the new widget
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.takeAt(i)
            if item.widget():
                item.widget().hide()
        
        self.content_layout.addWidget(widget)
        widget.show()
        
        # Show panel
        self.show()
        self.setFixedHeight(self.default_height)
        
        self.active_content = name
    
    def close_content(self):
        """Close the currently open content."""
        if not self.active_content:
            return
        
        button = self.toggle_buttons[self.active_content]
        widget = self.content_widgets[self.active_content]
        
        # Update button state
        button.setChecked(False)
        
        # Hide content
        widget.hide()
        self.hide()
        
        self.active_content = None
    
    def get_active_content(self) -> str | None:
        """Get the name of the currently active content."""
        return self.active_content
    
    def get_height(self) -> int:
        """Get the height of the bottom panel when visible."""
        if self.isVisible():
            return self.height()
        return 0
