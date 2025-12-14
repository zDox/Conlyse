from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QWheelEvent
from PyQt6.QtWidgets import QWidget


class OverviewBar(QWidget):
    """Overview bar showing full timeline with draggable viewport"""

    position_clicked = pyqtSignal(float)
    range_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(32)
        self.setMaximumHeight(32)
        self.visible_start = 0.0
        self.visible_end = 1.0
        self.current_position = 0.0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dragging = None
        self.drag_offset = 0.0

    def set_viewport(self, start, end):
        self.visible_start = start
        self.visible_end = end
        self.update()

    def set_position(self, pos):
        self.current_position = pos
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.setPen(QColor(255, 255, 255, 51))
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawRoundedRect(self.rect(), 4, 4)

        # Viewport indicator
        viewport_start_px = int(self.visible_start * self.width())
        viewport_width_px = int((self.visible_end - self.visible_start) * self.width())
        painter.setPen(QColor(59, 130, 246, 255))
        painter.setBrush(QColor(59, 130, 246, 51))
        painter.drawRoundedRect(viewport_start_px, 0, viewport_width_px, self.height(), 4, 4)

        # Viewport handles
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 180))
        painter.drawEllipse(viewport_start_px - 6, self.height() // 2 - 6, 12, 12)
        painter.drawEllipse(viewport_start_px + viewport_width_px - 6, self.height() // 2 - 6, 12, 12)

        # Current playhead
        playhead_x = int(self.current_position * self.width())
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRect(playhead_x - 2, 0, 4, self.height())
        painter.drawEllipse(playhead_x - 6, -6, 12, 12)
        painter.drawEllipse(playhead_x - 6, self.height() - 6, 12, 12)

    def mousePressEvent(self, event):
        x = event.position().x()
        normalized_x = x / self.width()

        if event.button() == Qt.MouseButton.RightButton:
            # Right click drags the entire viewport without selecting handles
            self.dragging = "range_right"
            self.drag_offset = (self.visible_start + self.visible_end) / 2 - normalized_x
            return

        elif event.button() == Qt.MouseButton.LeftButton:

            start_x = int(self.visible_start * self.width())
            if abs(x - start_x) < 12:
                self.dragging = "start"
                self.drag_offset = self.visible_start - normalized_x
                return

            end_x = int(self.visible_end * self.width())
            if abs(x - end_x) < 12:
                self.dragging = "end"
                self.drag_offset = self.visible_end - normalized_x
                return

            if start_x <= x <= end_x:
                self.dragging = "range"
                self.drag_offset = (self.visible_start + self.visible_end) / 2 - normalized_x
                return

            percent = max(0.0, min(1.0, normalized_x))
            self.position_clicked.emit(percent)

    def mouseMoveEvent(self, event):
        if self.dragging:
            x = event.position().x()
            normalized_x = max(0.0, min(1.0, x / self.width()))

            if self.dragging == "start":
                new_start = normalized_x + self.drag_offset
                self.visible_start = max(0.0, min(self.visible_end - 0.01, new_start))
                self.range_changed.emit(self.visible_start, self.visible_end)

            elif self.dragging == "end":
                new_end = normalized_x + self.drag_offset
                self.visible_end = max(self.visible_start + 0.01, min(1.0, new_end))
                self.range_changed.emit(self.visible_start, self.visible_end)

            elif self.dragging in ("range", "range_right"):
                center = normalized_x + self.drag_offset
                range_width = self.visible_end - self.visible_start
                new_start = center - range_width / 2
                new_end = center + range_width / 2
                # 'range' comes from left-click drag; 'range_right' from right-click drag

                if new_start < 0:
                    new_start = 0
                    new_end = range_width
                elif new_end > 1:
                    new_end = 1
                    new_start = 1 - range_width

                self.visible_start = new_start
                self.visible_end = new_end
                self.range_changed.emit(self.visible_start, self.visible_end)

            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self.dragging = None

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
