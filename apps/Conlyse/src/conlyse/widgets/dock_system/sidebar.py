"""
Sidebar widget for managing multiple docks in a JetBrains IDE-style interface.
Each sidebar can have multiple dock buttons, but only one dock can be open at a time.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from conlyse.utils.enums import DockType

if TYPE_CHECKING:
    pass


class Sidebar(QWidget):
    """
    A sidebar widget that manages multiple docks.
    Only one dock can be open at a time per sidebar.
    docks overlay the main content when opened.
    """
    
    def __init__(self, side: str = "left", parent=None, button_width: int = 40, dock_width: int = 300, bottom_dock_height: int=150):
        """
        Initialize the sidebar.
        
        Args:
            side: "left" or "right" to determine which side of the screen
            parent: Parent widget
            button_width: Width of the sidebar button strip
            dock_width: Width of the dock when opened
            bottom_dock_height: Callable that returns the default height of the bottom dock
        """
        super().__init__(parent)
        self.side = side
        self.button_width = button_width
        self.dock_width = dock_width
        self.docks: dict[DockType, tuple[QPushButton, QWidget]] = {}  # dock_name -> (button, dock_widget)
        self.active_dock = None
        self.bottom_dock_buttons: dict[DockType, QPushButton] = {}  # bottom_dock_name -> button
        self.bottom_dock_height: int = bottom_dock_height
        
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
        self.button_layout.addStretch()  # Stretch to push bottom dock buttons to bottom

        # Dock container
        self.dock_container = QWidget(self)
        self.dock_container.setObjectName("sidebar_dock_container")
        self.dock_container.setFixedWidth(dock_width)
        self.dock_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        self.dock_container.hide()

        self.dock_layout = QVBoxLayout(self.dock_container)
        self.dock_layout.setContentsMargins(0, 0, 0, 0)
        self.dock_layout.setSpacing(0)

        # Arrange widgets based on side
        if side == "left":
            self.main_layout.addWidget(self.button_strip)
            self.main_layout.addWidget(self.dock_container, 0, Qt.AlignmentFlag.AlignTop)
        else:
            self.main_layout.addWidget(self.dock_container, 0, Qt.AlignmentFlag.AlignTop)
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
        """Update the sidebar geometry based on parent size and active dock."""
        parent = self.parent()
        if parent is None:
            return

        parent_width = parent.width()
        parent_height = parent.height()

        # Entire sidebar widget takes full height (so button strip is full height)
        sidebar_height = parent_height
        
        # Dock container should stop where bottom dock starts
        dock_container_height = parent_height - self.bottom_dock_height
        
        # Set maximum height for dock container
        self.dock_container.setMaximumHeight(dock_container_height)

        if self.active_dock:
            # Show both button strip and dock
            width = self.button_width + self.dock_width
        else:
            # Show only button strip
            width = self.button_width
        if self.side == "left":
            self.setGeometry(0, 0, width, sidebar_height)
        else:
            self.setGeometry(parent_width - width, 0, width, sidebar_height)

    def add_bottom_dock_button(self, dock_type: DockType, label: str, callback):
        """
        Add a button for bottom dock control (only for left sidebar).
        
        Args:
            dock_type: Unique identifier for the bottom dock
            label: Text to display on the button
            callback: Function to call when button is clicked
        """
        if self.side != "left":
            return  # Bottom dock buttons only on left sidebar
        
        # Create button
        button = QPushButton(label, self.button_strip)
        button.setObjectName("bottom_dock_button")
        button.setFixedHeight(40)
        button.setCheckable(True)
        button.clicked.connect(callback)
        
        # Add button at the end (after the stretch)
        self.button_layout.addWidget(button)
        
        # Store button
        self.bottom_dock_buttons[dock_type] = button
    
    def set_bottom_dock_button_checked(self, dock_type: DockType, checked: bool):
        """
        Set the checked state of a bottom dock button.
        
        Args:
            dock_type: Name of the bottom dock button
            checked: Whether to check or uncheck the button
        """
        if dock_type in self.bottom_dock_buttons:
            self.bottom_dock_buttons[dock_type].setChecked(checked)
    
    def add_dock(self, dock_type: DockType, label: str, dock_widget: QWidget):
        """
        Add a dock to the sidebar.
        
        Args:
            dock_type: Unique identifier for the dock
            label: Text to display on the button
            dock_widget: The widget to show when dock is opened
        """
        # Create button
        button = QPushButton(label, self.button_strip)
        button.setObjectName("sidebar_dock_button")
        button.setFixedHeight(40)
        button.setCheckable(True)
        button.clicked.connect(lambda checked: self.toggle_dock(dock_type))
        
        # Insert button before the stretch
        self.button_layout.insertWidget(self.button_layout.count() - 1, button)
        
        # Store dock
        dock_widget.setParent(self.dock_container)
        dock_widget.hide()
        self.docks[dock_type] = (button, dock_widget)
    
    def toggle_dock(self, dock_type: DockType):
        """
        Toggle a dock open or closed.
        If another dock is open, close it first.
        
        Args:
            dock_type: Name of the dock to toggle
        """
        if dock_type not in self.docks:
            return
        

        # If clicking the currently open dock, close it
        if self.active_dock == dock_type:
            self.close_dock()
        else:
            # Close currently open dock if any
            if self.active_dock:
                self.close_dock()
            # Open the new dock
            self.open_dock(dock_type)
    
    def open_dock(self, dock_type: DockType):
        """
        Open a specific dock.
        
        Args:
            dock_type: Name of the dock to open
        """
        if dock_type not in self.docks:
            return
        
        # Close any currently open dock first
        if self.active_dock:
            self.close_dock()
        
        button, dock_widget = self.docks[dock_type]
        
        # Update button state
        button.setChecked(True)
        
        # Clear dock layout and add the new dock
        for i in reversed(range(self.dock_layout.count())):
            item = self.dock_layout.takeAt(i)
            if item.widget():
                item.widget().hide()
        
        self.dock_layout.addWidget(dock_widget)
        dock_widget.show()
        
        # Show dock container
        self.dock_container.show()
        
        self.active_dock = dock_type
        self._update_geometry()
    
    def close_dock(self):
        """Close the currently open dock."""
        if not self.active_dock:
            return
        
        button, dock_widget = self.docks[self.active_dock]
        
        # Update button state
        button.setChecked(False)
        
        # Hide dock
        dock_widget.hide()
        self.dock_container.hide()
        
        self.active_dock = None
        self._update_geometry()
    
    def update_geometry(self):
        """Public method to update sidebar geometry."""
        self._update_geometry()
    
    def get_current_width(self) -> int:
        """Get the current width of the sidebar."""
        if self.active_dock:
            return self.button_width + self.dock_width
        return self.button_width
    
    def get_active_dock(self) -> str | None:
        """Get the name of the currently active dock."""
        return self.active_dock
