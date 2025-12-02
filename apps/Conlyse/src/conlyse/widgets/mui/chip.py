from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QWidget


class CChip(QWidget):
    def __init__(self, text: str, variant: str = "outlined", color: str = "primary", parent=None):
        super().__init__(parent)
        self.setProperty("variant", variant)
        self.setProperty("color", color)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 2, 8, 2)

        self.text_label = QLabel(text, self)
        self.layout.addWidget(self.text_label)

    def set_variant(self, variant: str):
        """Set the button variant (e.g., 'default', 'outlined', 'text')."""
        self.setProperty("variant", variant)

    def set_color(self, color: str):
        """Set the button color (e.g., 'primary', 'secondary', 'success')."""
        self.setProperty("color", color)

    def set_text(self, text: str):
        """Set the chip text."""
        self.text_label.setText(text)

    def refresh(self):
        self.style().unpolish(self)
        self.style().polish(self)