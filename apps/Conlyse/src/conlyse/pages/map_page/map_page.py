import logging

from PyQt6.QtCore import QTimer
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget
from conflict_interface.data_types.point import Point
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.logger_config import setup_library_logger

from conlyse.logger import get_logger
from conlyse.logger import setup_logger
from conlyse.pages.map_page.map import Map  # assuming this is correct

logger = get_logger()


class MapPage(QWidget):
    def __init__(self, ritf: ReplayInterface):
        super().__init__()
        self.ritf = ritf
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Configure OpenGL format BEFORE creating the Map widget
        fmt = QSurfaceFormat()
        fmt.setVersion(4, 1)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(fmt)

        self.map_widget: Map = Map(ritf)
        layout.addWidget(self.map_widget)
        self.setLayout(layout)

        # State for mouse dragging and keyboard input
        self.last_mouse_pos: Point | None = None
        self.dragging = False
        self.pressed_keys: set[int] = set()

    def setup(self):
        pass

    # ---- Input event handlers ----
    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.pressed_keys.add(event.key())

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.pressed_keys.discard(event.key())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = Point(event.pos().x(), event.pos().y())
            self.dragging = True

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            event_pos = Point(event.pos().x(), event.pos().y())

            delta = event_pos - self.last_mouse_pos
            self.last_mouse_pos = event_pos

            self.map_widget.handle_camera_move(-delta.x, -delta.y)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        new_zoom = self.map_widget.camera.zoom * zoom_factor
        x, y = event.position().x(), event.position().y()
        self.map_widget.camera.zoom_to(new_zoom, x, y)
        self.map_widget.update()

    # ---- Update Camera ----
    def update_camera(self):
        step = 10
        config = {
            Qt.Key.Key_W: (0, -step),
            Qt.Key.Key_S: (0, step),
            Qt.Key.Key_A: (-step, 0),
            Qt.Key.Key_D: (step, 0),
        }
        any_updated = False
        for key, (dx, dy) in config.items():
            if key in self.pressed_keys:
                self.map_widget.handle_camera_move(dx, dy)
                any_updated = True
        if any_updated:
            self.map_widget.update()

    def update(self):
        self.update_camera()

    def clean_up(self):
        pass


if __name__ == '__main__':
    setup_logger(logging.DEBUG)
    setup_library_logger(logging.DEBUG)
    app = QApplication([])
    ritf = ReplayInterface("test_replay.bin")
    ritf.open()
    print(ritf.get_provinces_by_name("Wyoming").id)
    map_page = MapPage(ritf)
    map_page.setup()
    map_page.resize(800, 600)
    map_page.show()
    # Timer for smooth continuous key movement
    timer = QTimer(map_page)
    timer.timeout.connect(map_page.update_camera)
    timer.start(16)  # ~60 FPS
    app.exec()
