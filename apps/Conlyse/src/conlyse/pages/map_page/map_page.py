import logging

from PyQt6.QtCore import QEvent
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtGui import QShortcut
from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from conflict_interface.data_types.point import Point

from conlyse.logger import get_logger
from conlyse.logger import setup_logger
from conlyse.pages.map_page.map import Map  # assuming this is correct

logger = get_logger()


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

        self.map_widget: Map = Map()
        layout.addWidget(self.map_widget)
        self.setLayout(layout)

        self.last_mouse_pos: Point | None = None
        self.dragging = False

    def setup(self):
        self.setup_keybindings()

    def setup_keybindings(self):
        movements = {
            "w": (0, 10),
            "s": (0, -10),
            "a": (-10, 0),
            "d": (10, 0),
        }
        for key, (move_dx, move_dy) in movements.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda dx=move_dx, dy=move_dy: self.map_widget.handle_camera_move(dx, dy))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = Point(event.pos().x(), event.pos().y())
            self.dragging = True

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            event_pos = Point(event.pos().x(), event.pos().y())

            delta = event_pos - self.last_mouse_pos
            self.last_mouse_pos = event_pos

            self.map_widget.handle_camera_move(-delta.x, delta.y)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        new_zoom = self.map_widget.camera.zoom * zoom_factor
        print("Wheel event:", delta, "New zoom:", new_zoom)
        x, y = event.position().x(), event.position().y()
        print("Mouse position:", x, y)
        self.map_widget.camera.zoom_to(new_zoom, x, y)
        self.map_widget.update()

    def update(self):
        pass

    def clean_up(self):
        pass


if __name__ == '__main__':
    setup_logger(logging.DEBUG)
    app = QApplication([])
    map_page = MapPage()
    map_page.setup()
    map_page.resize(800, 600)
    map_page.show()

    app.exec()
