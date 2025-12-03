import logging

from PyQt6.QtGui import QKeySequence
from PyQt6.QtGui import QShortcut
from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

from conlyse.pages.map_page.map import Map  # assuming this is correct

logger = logging.getLogger(__name__)


class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Configure OpenGL format BEFORE creating the Map widget
        fmt = QSurfaceFormat()
        fmt.setVersion(4, 1)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(fmt)

        self.map_widget = Map()
        layout.addWidget(self.map_widget)
        self.setLayout(layout)

    def setup(self):
        self.setup_keybindings()

    def setup_keybindings(self):
        movements = {
            "w": (0, 10),
            "s": (0, -10),
            "a": (-10, 0),
            "d": (10, 0),
        }
        for key, (dx, dy) in movements.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda dx=dx, dy=dy: self.map_widget.handle_camera_move(dx, dy))

    def update(self):
        pass

    def clean_up(self):
        pass


if __name__ == '__main__':
    app = QApplication([])

    map_page = MapPage()
    map_page.setup()
    map_page.resize(800, 600)
    map_page.show()

    app.exec()
