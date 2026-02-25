from PySide6.QtCore import Qt, Property as pyqtProperty
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel
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
            icon_size: int = 16,
            parent=None
    ):
        super().__init__(parent)

        self.icon_name = icon_name
        self.icon_position = icon_position
        self.icon_size = icon_size
        self._icon_color_value = DEFAULT_ICON_COLOR
        self.icon_label = None
        self.text_label = None

        self.setProperty("variant", variant)
        self.setProperty("color", color)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Create layout for button content
        if icon_name:
            self._setup_with_icon(text)
        else:
            self.setText(text)

    def _create_icon_label(self) -> QLabel:
        """Create and return a bare icon QLabel."""
        label = QLabel(self)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        label.setObjectName("icon_label")
        return label

    def _setup_with_icon(self, text: str):
        """Setup button with icon and text layout"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)

        layout.addStretch()

        # Icon at start
        if self.icon_position == "start":
            self.icon_label = self._create_icon_label()
            layout.addWidget(self.icon_label)

        # Text label
        self.text_label = QLabel(text, self)
        self.text_label.setObjectName("text_label")
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.text_label)

        # Icon at end
        if self.icon_position == "end":
            self.icon_label = self._create_icon_label()
            layout.addWidget(self.icon_label)

        layout.addStretch()

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
        if self.icon_label is None or not self.icon_name:
            return

        icon = qta.icon(self.icon_name, color=self._icon_color_value)
        self.icon_label.setPixmap(icon.pixmap(self.icon_size, self.icon_size))

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

    def set_text(self, text: str):
        """Set the button text."""
        if self.text_label is not None:
            self.text_label.setText(text)
        else:
            self.setText(text)

    def setText(self, text: str):
        """Override setText to handle icon layout"""
        if self.text_label is not None:
            self.text_label.setText(text)
        else:
            super().setText(text)

    def text(self):
        """Override text to handle icon layout"""
        if self.text_label is not None:
            return self.text_label.text()
        else:
            return super().text()
