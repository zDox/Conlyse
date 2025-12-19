"""
Bottom dock widget for ReplayPage.
Can display different content like TimelineControls.
Overlays the map between the two sidebars when active.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout

from conlyse.utils.enums import DockType

if TYPE_CHECKING:
    pass


class BottomDockContainer(QWidget):
    """
    A bottom dock widget that overlays the map content.
    Positioned between left and right sidebars, controlled by buttons in the left sidebar.
    """
    
    def __init__(self, parent=None, default_height: int = 150, left_sidebar_button_width=40, right_sidebar_button_width=40):
        """
        Initialize the bottom dock.
        
        Args:
            parent: Parent widget
            default_height: Default height of the dock when visible
            left_sidebar_button_width: width of the left sidebar's button strip (excluding any open dock width)
            right_sidebar_button_width: width of the right sidebar's button strip (excluding any open dock width)
        """
        super().__init__(parent)
        self.default_height = default_height
        self.active_content: DockType | None = None
        self.docks: dict[DockType, QWidget] = {}  # dock_name -> widget
        self.left_sidebar_button_width = left_sidebar_button_width
        self.right_sidebar_button_width = right_sidebar_button_width
        
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

        
        # Position at bottom, between sidebars
        x = self.left_sidebar_button_width
        width = parent_width - self.left_sidebar_button_width - self.right_sidebar_button_width
        y = parent_height - self.default_height
        
        self.setGeometry(x, y, width, self.default_height)
    
    def add_content(self, dock_type: DockType, widget: QWidget):
        """
        Add a content widget that can be displayed in the bottom dock.
        
        Args:
            dock_type: Unique DockType for the content
            widget: The widget to show when content is selected
        """
        # Store content
        widget.setParent(self)
        widget.hide()
        self.docks[dock_type] = widget
    
    def toggle_content(self, dock_type: DockType):
        """
        Toggle a content widget open or closed.
        
        Args:
            dock_type: DockType of the dock to toggle
        """
        if dock_type not in self.docks:
            return

        # If clicking the currently active content, close it
        if self.active_content == dock_type:
            self.close_dock()
        else:
            # Open the new content
            self.open_dock(dock_type)
    
    def open_dock(self, dock_type: DockType):
        """
        Open a specific content widget.
        
        Args:
            dock_type: DockType enum value for the content to open
        """
        if dock_type not in self.docks:
            return

        # Close any currently active content first
        if self.active_content:
            self.close_dock()
        widget = self.docks[dock_type]
        
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
        
        self.active_content = dock_type
    
    def close_dock(self):
        """Close the currently open content."""
        if not self.active_content:
            return
        
        widget = self.docks[self.active_content]
        
        # Hide content
        widget.hide()
        self.hide()
        
        self.active_content = None
    
    def get_active_dock(self) -> DockType | None:
        """Get the DockType of the currently active content."""
        return self.active_content
    
    def get_default_height(self) -> int:
        """Get the default height of the bottom dock."""
        return self.default_height
    
    def update_geometry(self):
        """Public method to update bottom dock geometry."""
        self._update_geometry()
