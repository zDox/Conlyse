from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from PyQt6.QtCore import Qt, pyqtProperty
from PyQt6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QWidget
import qtawesome as qta

DEFAULT_ICON_COLOR = "#FFFFFF"


class CButton(QPushButton):
    """A custom button with predefined styles and optional icon."""

    def __init__(
            self,
            text: str = "Button",
            variant: str = "default",
            color: str = "primary",
            icon_name: str = None,
            icon_position: str = "start",  # "start" or "end"
            parent=None
    ):
        super().__init__(parent)

        self.icon_name = icon_name
        self.icon_position = icon_position
        self._icon_color_value = DEFAULT_ICON_COLOR

        self.setProperty("variant", variant)
        self.setProperty("color", color)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Create layout for button content
        if icon_name:
            self._setup_with_icon(text)
        else:
            self.setText(text)

    def _setup_with_icon(self, text: str):
        """Setup button with icon and text layout"""
        # Create a container widget for the layout
        container = QWidget(self)
        container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # Icon at start
        if self.icon_position == "start":
            self.icon_label = QLabel(container)
            self.icon_label.setObjectName("icon_label")
            layout.addWidget(self.icon_label)

        # Text label
        self.text_label = QLabel(text, container)
        self.text_label.setObjectName("text_label")
        # Remove center alignment to keep text and icon close
        layout.addWidget(self.text_label)

        # Icon at end
        if self.icon_position == "end":
            self.icon_label = QLabel(container)
            self.icon_label.setObjectName("icon_label")
            layout.addWidget(self.icon_label)

        # Add stretch to center the content group
        layout.insertStretch(0)  # Stretch before content
        layout.addStretch()  # Stretch after content

        # Make the container fill the button
        button_layout = QHBoxLayout(self)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(container)

        # Ensure button sizes properly
        self.adjustSize()

        self._update_icon()

    @pyqtProperty(str)
    def iconColor(self):
        return self._icon_color_value

    @iconColor.setter
    def iconColor(self, color: str):
        if self._icon_color_value != color:
            self._icon_color_value = color
            self._update_icon()

    def _update_icon(self):
        """Update icon with current color"""
        if not hasattr(self, 'icon_label') or not self.icon_name:
            return

        icon = qta.icon(self.icon_name, color=self._icon_color_value)
        self.icon_label.setPixmap(icon.pixmap(16, 16))

    def set_variant(self, variant: str):
        """Set the button variant (e.g., 'default', 'outlined', 'text')."""
        self.setProperty("variant", variant)
        self.style().unpolish(self)
        self.style().polish(self)
        self._update_icon()  # Update icon color when style changes

    def set_color(self, color: str):
        """Set the button color (e.g., 'primary', 'secondary', 'success')."""
        self.setProperty("color", color)
        self.style().unpolish(self)
        self.style().polish(self)
        self._update_icon()  # Update icon color when style changes

    def setText(self, text: str):
        """Override setText to handle icon layout"""
        if hasattr(self, 'text_label'):
            self.text_label.setText(text)
        else:
            super().setText(text)

    def text(self):
        """Override text to handle icon layout"""
        if hasattr(self, 'text_label'):
            return self.text_label.text()
        else:
            return super().text()