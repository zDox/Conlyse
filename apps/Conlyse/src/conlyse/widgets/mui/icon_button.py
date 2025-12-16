from PySide6.QtCore import QSize
from PySide6.QtCore import Qt, Property as pyqtProperty
from PySide6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QWidget
import qtawesome as qta


class CIconButton(QPushButton):
    """A button that displays only an icon."""

    def __init__(
        self,
        icon_name: str,
        color: str = "primary",
        size: int = 24,
        parent=None
    ):
        super().__init__(parent)
        self.setMaximumSize(QSize(size, size))
        self.icon_name = icon_name
        self.setProperty("color", color)
        self._icon_color_value = "#FFFFFF"
        self._icon_size = size

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Setup icon layout
        self._setup_icon()

    def _setup_icon(self):
        """Setup the icon label in the button."""
        self.icon_label = QLabel(self)
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_icon()

    @pyqtProperty(str)
    def iconColor(self):
        return self._icon_color_value

    @iconColor.setter
    def iconColor(self, color: str):
        if self._icon_color_value != color:
            self._icon_color_value = color
            self._update_icon()

    @pyqtProperty(int)
    def iconSize(self):
        return self._icon_size

    @iconSize.setter
    def iconSize(self, size: int):
        if self._icon_size != size:
            self._icon_size = size
            self._update_icon()

    def _update_icon(self):
        """Update the icon with the current color and size."""
        if not hasattr(self, 'icon_label') or not self.icon_name:
            return

        icon = qta.icon(self.icon_name, color=self._icon_color_value)
        self.icon_label.setPixmap(icon.pixmap(self._icon_size, self._icon_size))

    def set_icon(self, icon_name: str):
        """Change the icon dynamically."""
        self.icon_name = icon_name
        self._update_icon()

    def set_icon_color(self, color: str):
        """Change the icon color dynamically."""
        self.setProperty("color", color)

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
