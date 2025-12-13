from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtWidgets import QWidget


from conlyse.widgets.mui.icon_button import CIconButton
if TYPE_CHECKING:
    from conlyse.app import App

class Header(QWidget):
    """A reusable header bar with a burger menu button."""

    def __init__(self, app: App, title: str = "My Application", parent=None):
        super().__init__(parent)
        self.app = app

        # --- Layout setup ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # --- Burger menu button ---
        self.menu_button = CIconButton("mdi.menu", "primary",size=40, parent=self)
        self.menu_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_button.setToolTip("Open menu")


        # --- Title label ---
        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("headerTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # --- Add widgets to layout ---
        layout.addWidget(self.menu_button)
        layout.addWidget(self.title_label)

        # Placeholder stretch for right side (optional icons later)
        layout.addStretch()

    def set_drawer_toggle_function(self, toggle_function):
        """Set the function to be called when the menu button is clicked."""
        self.menu_button.clicked.connect(toggle_function)
