from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QWheelEvent
from PyQt6.QtWidgets import QWidget


class SimplePositionSlider(QWidget):
    """Simple slider showing only current position within a range"""

    value_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(48)
        self.position = 0.5  # normalized 0-1 within the visible range
        self.dragging = False
        self.setMouseTracking(True)

    def set_position(self, pos):
        self.position = max(0.0, min(1.0, pos))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background track
        track_y = self.height() // 2 - 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 51))
        painter.drawRoundedRect(0, track_y, self.width(), 12, 6, 6)

        # Progress up to current position
        pos_x = int(self.position * self.width())
        painter.setBrush(QColor(59, 130, 246))
        painter.drawRoundedRect(0, track_y, pos_x, 12, 6, 6)

        # Current position indicator (playhead)
        painter.setBrush(QColor(34, 211, 238))
        painter.drawEllipse(pos_x - 12, self.height() // 2 - 12, 24, 24)
        painter.setBrush(QColor(103, 232, 249, 150))
        painter.drawEllipse(pos_x - 8, self.height() // 2 - 8, 16, 16)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.update_position_from_mouse(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            self.update_position_from_mouse(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def update_position_from_mouse(self, event: QMouseEvent):
        x = event.position().x()
        normalized_x = max(0.0, min(1.0, x / self.width()))
        self.position = normalized_x
        self.value_changed.emit(self.position)
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
