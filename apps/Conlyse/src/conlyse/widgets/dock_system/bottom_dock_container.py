"""
Bottom dock widget for ReplayPage.
Can display different content like TimelineControls.
Overlays the map between the two sidebars when active.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout

if TYPE_CHECKING:
    pass


class BottomDockContainer(QWidget):
    """
    A bottom dock widget that overlays the map content.
    Positioned between left and right sidebars, controlled by buttons in the left sidebar.
    """
    
    def __init__(self, parent=None, default_height: int = 150, left_sidebar_width_callback=None, right_sidebar_width_callback=None):
        """
        Initialize the bottom dock.
        
        Args:
            parent: Parent widget
            default_height: Default height of the dock when visible
            left_sidebar_width_callback: Callable that returns the width of the left sidebar
            right_sidebar_width_callback: Callable that returns the width of the right sidebar
        """
        super().__init__(parent)
        self.default_height = default_height
        self.active_content = None
        self.content_widgets = {}  # dock_name -> widget
        self.left_sidebar_width_callback = left_sidebar_width_callback
        self.right_sidebar_width_callback = right_sidebar_width_callback
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("bottom_dock")
        
        # Content layout
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Start hidden
        self.hide()
        
        # Listen for parent resize
        if parent is not None:
            parent.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle parent resize events to update geometry."""
        if event.type() == QEvent.Type.Resize:
            self._update_geometry()
        return super().eventFilter(obj, event)
    
    def _update_geometry(self):
        """Update the bottom dock geometry based on parent size and sidebars."""
        parent = self.parent()
        if parent is None or not self.isVisible():
            return
        
        parent_width = parent.width()
        parent_height = parent.height()
        
        # Get sidebar widths
        left_width = 0
        if self.left_sidebar_width_callback:
            left_width = self.left_sidebar_width_callback()
        
        right_width = 0
        if self.right_sidebar_width_callback:
            right_width = self.right_sidebar_width_callback()
        
        # Position at bottom, between sidebars
        x = left_width
        width = parent_width - left_width - right_width
        y = parent_height - self.default_height
        
        self.setGeometry(x, y, width, self.default_height)
    
    def add_content(self, name: str, widget: QWidget):
        """
        Add a content widget that can be displayed in the bottom dock.
        
        Args:
            name: Unique identifier for the content
            widget: The widget to show when content is selected
        """
        # Store content
        widget.setParent(self)
        widget.hide()
        self.content_widgets[name] = widget
    
    def toggle_content(self, name: str):
        """
        Toggle a content widget open or closed.
        
        Args:
            name: Name of the content to toggle
        """
        if name not in self.content_widgets:
            return
        
        # If clicking the currently active content, close it
        if self.active_content == name:
            self.close_content()
        else:
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
        
        widget = self.content_widgets[name]
        
        # Clear content layout and add the new widget
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.takeAt(i)
            if item.widget():
                item.widget().hide()
        
        self.content_layout.addWidget(widget)
        widget.show()
        
        # Show dock
        self.show()
        self.raise_()
        self._update_geometry()
        
        self.active_content = name
    
    def close_content(self):
        """Close the currently open content."""
        if not self.active_content:
            return
        
        widget = self.content_widgets[self.active_content]
        
        # Hide content
        widget.hide()
        self.hide()
        
        self.active_content = None
    
    def get_active_content(self) -> str | None:
        """Get the name of the currently active content."""
        return self.active_content
    
    def get_default_height(self) -> int:
        """Get the default height of the bottom dock."""
        return self.default_height
    
    def update_geometry(self):
        """Public method to update bottom dock geometry."""
        self._update_geometry()
