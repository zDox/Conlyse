from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtWidgets import QWidget



class Header(QWidget):
    """A reusable header bar with a burger menu button."""

    def __init__(self, title: str = "My Application"):
        super().__init__()

        # --- Layout setup ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # --- Burger menu button ---
        self.menu_button = QPushButton()
        self.menu_button.setObjectName("menuButton")
        self.menu_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_button.setToolTip("Open menu")
        self.menu_button.setIcon(QIcon.fromTheme("application-menu"))  # fallback icon
        self.menu_button.setText("☰")  # Unicode fallback if no icon theme
        self.menu_button.setFixedSize(36, 36)

        # --- Title label ---
        self.title_label = QLabel(title)
        self.title_label.setObjectName("headerTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # --- Add widgets to layout ---
        layout.addWidget(self.menu_button)
        layout.addWidget(self.title_label)

        # Placeholder stretch for right side (optional icons later)
        layout.addStretch()

