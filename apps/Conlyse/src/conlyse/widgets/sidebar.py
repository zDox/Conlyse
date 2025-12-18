"""
Sidebar widget for managing multiple panels in a JetBrains IDE-style interface.
Each sidebar can have multiple panel buttons, but only one panel can be open at a time.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QPropertyAnimation, QPoint, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy

if TYPE_CHECKING:
    pass


class Sidebar(QWidget):
    """
    A sidebar widget that manages multiple panels.
    Only one panel can be open at a time per sidebar.
    Panels overlay the main content when opened.
    """
    
    def __init__(self, side: str = "left", parent=None, button_width: int = 40, panel_width: int = 300):
        """
        Initialize the sidebar.
        
        Args:
            side: "left" or "right" to determine which side of the screen
            parent: Parent widget
            button_width: Width of the sidebar button strip
            panel_width: Width of the panel when opened
        """
        super().__init__(parent)
        self.side = side
        self.button_width = button_width
        self.panel_width = panel_width
        self.panels = {}  # panel_name -> (button, panel_widget)
        self.active_panel = None
        self.bottom_panel_buttons = {}  # bottom_panel_name -> button
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("sidebar")
        
        # Main layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Button strip
        self.button_strip = QWidget(self)
        self.button_strip.setObjectName("sidebar_button_strip")
        self.button_strip.setFixedWidth(button_width)
        self.button_strip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        
        self.button_layout = QVBoxLayout(self.button_strip)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        self.button_layout.addStretch()  # Stretch to push bottom panel buttons to bottom
        
        # Panel container
        self.panel_container = QWidget(self)
        self.panel_container.setObjectName("sidebar_panel_container")
        self.panel_container.setFixedWidth(panel_width)
        self.panel_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.panel_container.hide()
        
        self.panel_layout = QVBoxLayout(self.panel_container)
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        self.panel_layout.setSpacing(0)
        
        # Arrange widgets based on side
        if side == "left":
            self.main_layout.addWidget(self.button_strip)
            self.main_layout.addWidget(self.panel_container)
        else:
            self.main_layout.addWidget(self.panel_container)
            self.main_layout.addWidget(self.button_strip)
        
        # Listen for parent resize
        if parent is not None:
            parent.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle parent resize events to update geometry."""
        if event.type() == QEvent.Type.Resize:
            self._update_geometry()
        return super().eventFilter(obj, event)
    
    def _update_geometry(self):
        """Update the sidebar geometry based on parent size and active panel."""
        parent = self.parent()
        if parent is None:
            return
        
        parent_width = parent.width()
        parent_height = parent.height()
        
        # Sidebar is now full height
        sidebar_height = parent_height
        
        if self.active_panel:
            # Show both button strip and panel
            width = self.button_width + self.panel_width
        else:
            # Show only button strip
            width = self.button_width
        
        if self.side == "left":
            self.setGeometry(0, 0, width, sidebar_height)
        else:
            self.setGeometry(parent_width - width, 0, width, sidebar_height)
    
    def add_bottom_panel_button(self, name: str, label: str, callback):
        """
        Add a button for bottom panel control (only for left sidebar).
        
        Args:
            name: Unique identifier for the bottom panel
            label: Text to display on the button
            callback: Function to call when button is clicked
        """
        if self.side != "left":
            return  # Bottom panel buttons only on left sidebar
        
        # Create button
        button = QPushButton(label, self.button_strip)
        button.setObjectName("bottom_panel_button")
        button.setFixedHeight(40)
        button.setCheckable(True)
        button.clicked.connect(callback)
        
        # Add button at the end (after the stretch)
        self.button_layout.addWidget(button)
        
        # Store button
        self.bottom_panel_buttons[name] = button
    
    def set_bottom_panel_button_checked(self, name: str, checked: bool):
        """
        Set the checked state of a bottom panel button.
        
        Args:
            name: Name of the bottom panel button
            checked: Whether to check or uncheck the button
        """
        if name in self.bottom_panel_buttons:
            self.bottom_panel_buttons[name].setChecked(checked)
    
    def add_panel(self, name: str, label: str, panel_widget: QWidget):
        """
        Add a panel to the sidebar.
        
        Args:
            name: Unique identifier for the panel
            label: Text to display on the button
            panel_widget: The widget to show when panel is opened
        """
        # Create button
        button = QPushButton(label, self.button_strip)
        button.setObjectName("sidebar_panel_button")
        button.setFixedHeight(40)
        button.setCheckable(True)
        button.clicked.connect(lambda checked: self.toggle_panel(name))
        
        # Insert button before the stretch
        self.button_layout.insertWidget(self.button_layout.count() - 1, button)
        
        # Store panel
        panel_widget.setParent(self.panel_container)
        panel_widget.hide()
        self.panels[name] = (button, panel_widget)
    
    def toggle_panel(self, name: str):
        """
        Toggle a panel open or closed.
        If another panel is open, close it first.
        
        Args:
            name: Name of the panel to toggle
        """
        if name not in self.panels:
            return
        
        button, panel_widget = self.panels[name]
        
        # If clicking the currently open panel, close it
        if self.active_panel == name:
            self.close_panel()
        else:
            # Close currently open panel if any
            if self.active_panel:
                self.close_panel()
            # Open the new panel
            self.open_panel(name)
    
    def open_panel(self, name: str):
        """
        Open a specific panel.
        
        Args:
            name: Name of the panel to open
        """
        if name not in self.panels:
            return
        
        # Close any currently open panel first
        if self.active_panel:
            self.close_panel()
        
        button, panel_widget = self.panels[name]
        
        # Update button state
        button.setChecked(True)
        
        # Clear panel layout and add the new panel
        for i in reversed(range(self.panel_layout.count())):
            item = self.panel_layout.takeAt(i)
            if item.widget():
                item.widget().hide()
        
        self.panel_layout.addWidget(panel_widget)
        panel_widget.show()
        
        # Show panel container
        self.panel_container.show()
        
        self.active_panel = name
        self._update_geometry()
    
    def close_panel(self):
        """Close the currently open panel."""
        if not self.active_panel:
            return
        
        button, panel_widget = self.panels[self.active_panel]
        
        # Update button state
        button.setChecked(False)
        
        # Hide panel
        panel_widget.hide()
        self.panel_container.hide()
        
        self.active_panel = None
        self._update_geometry()
    
    def update_geometry(self):
        """Public method to update sidebar geometry."""
        self._update_geometry()
    
    def get_current_width(self) -> int:
        """Get the current width of the sidebar."""
        if self.active_panel:
            return self.button_width + self.panel_width
        return self.button_width
    
    def get_active_panel(self) -> str | None:
        """Get the name of the currently active panel."""
        return self.active_panel
