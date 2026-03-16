from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QWidget


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
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(6)

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

        # API / auth status label on the right
        self.api_status_label = QLabel("API: Unknown")
        self.api_status_label.setObjectName("apiStatusLabel")
        self.api_status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.api_status_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.api_status_label)

        layout.addLayout(self.actions_layout)

    def set_drawer_toggle_function(self, toggle_function):
        """Set the function to be called when the menu button is clicked."""
        self.menu_button.clicked.connect(toggle_function)

    def set_actions(self, widgets: list[QWidget] | None):
        """Replace the right-side actions with the provided widgets."""
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        if not widgets:
            return

        for widget in widgets:
            self.actions_layout.addWidget(widget)

    def set_api_status(self, text: str):
        """Update the right-side API status label."""
        self.api_status_label.setText(text)
