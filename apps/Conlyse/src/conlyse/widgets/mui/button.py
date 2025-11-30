from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton


class CButton(QPushButton):
    """A custom button with predefined styles."""

    def __init__(self, text: str = "Button", variant: str = "default", color: str = "primary"):
        super().__init__(text)
        self.setProperty("variant", variant)
        self.setProperty("color", color)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_variant(self, variant: str):
        """Set the button variant (e.g., 'default', 'outlined', 'text')."""
        self.setProperty("variant", variant)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_color(self, color: str):
        """Set the button color (e.g., 'primary', 'secondary', 'success')."""
        self.setProperty("color", color)
        self.style().unpolish(self)
        self.style().polish(self)