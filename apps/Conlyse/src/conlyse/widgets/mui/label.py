from PySide6.QtCore import Qt, Property as pyqtProperty
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget, QSizePolicy
import qtawesome as qta

from conlyse.logger import get_logger

logger = get_logger()

DEFAULT_ICON_COLOR = "#E0E0E0"


class CLabel(QWidget):
    def __init__(
            self,
            text: str,
            icon_name: str = None,
            icon_color: str = "primary",
            icon_position: str = "start",  # "start" or "end"
            icon_size: int = 16,
            parent=None
    ):
        super().__init__(parent)

        # Make widget styleable
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("iconColorType", icon_color)

        # Store icon info for later use
        self.icon_name = icon_name
        self.icon_size = icon_size
        self._icon_color_value = DEFAULT_ICON_COLOR
        self.icon_label = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # If icon given and we want it at the start
        if icon_name and icon_position == "start":
            self.icon_label = self._create_icon_label(icon_color)
            layout.addWidget(self.icon_label)
            self._update_icon()

        # The text part
        self.text_label = QLabel(text, self)
        self.text_label.setObjectName("text_label")
        # Prevent the text label from expanding to fill the whole row; let it take minimal width
        self.text_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.text_label)

        # If icon at the end
        if icon_name and icon_position == "end":
            self.icon_label = self._create_icon_label(icon_color)
            layout.addWidget(self.icon_label)
            self._update_icon()

        self.setLayout(layout)

    def _create_icon_label(self, icon_color: str) -> QLabel:
        """Create and return a configured icon QLabel."""
        label = QLabel(self)
        label.setObjectName("icon_label")
        label.setProperty("color", icon_color)
        label.setFixedSize(self.icon_size, self.icon_size)
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

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

    def set_icon(self, icon_name: str):
        """Set or update the icon."""
        self.icon_name = icon_name
        self._update_icon()

    def set_text(self, text: str):
        """Set the label text"""
        self.text_label.setText(text)
