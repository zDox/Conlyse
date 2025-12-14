import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QSlider, QComboBox,
                             QSpinBox, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QPalette, QColor, QPainter, QLinearGradient, QMouseEvent, QWheelEvent


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

        # Current position indicator (playhead) - cyan/teal color
        painter.setBrush(QColor(34, 211, 238))  # Cyan-400
        painter.drawEllipse(pos_x - 12, self.height() // 2 - 12, 24, 24)

        # Inner highlight for depth
        painter.setBrush(QColor(103, 232, 249, 150))  # Cyan-300 semi-transparent
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
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            normalized_x = x / self.width()

            start_x = int(self.visible_start * self.width())
            if abs(x - start_x) < 12:
                self.dragging = 'start'
                self.drag_offset = self.visible_start - normalized_x
                return

            end_x = int(self.visible_end * self.width())
            if abs(x - end_x) < 12:
                self.dragging = 'end'
                self.drag_offset = self.visible_end - normalized_x
                return

            if start_x <= x <= end_x:
                self.dragging = 'range'
                self.drag_offset = (self.visible_start + self.visible_end) / 2 - normalized_x
                return

            percent = max(0.0, min(1.0, normalized_x))
            self.position_clicked.emit(percent)

    def mouseMoveEvent(self, event):
        if self.dragging:
            x = event.position().x()
            normalized_x = max(0.0, min(1.0, x / self.width()))

            if self.dragging == 'start':
                new_start = normalized_x + self.drag_offset
                self.visible_start = max(0.0, min(self.visible_end - 0.01, new_start))
                self.range_changed.emit(self.visible_start, self.visible_end)

            elif self.dragging == 'end':
                new_end = normalized_x + self.drag_offset
                self.visible_end = max(self.visible_start + 0.01, min(1.0, new_end))
                self.range_changed.emit(self.visible_start, self.visible_end)

            elif self.dragging == 'range':
                center = normalized_x + self.drag_offset
                range_width = self.visible_end - self.visible_start
                new_start = center - range_width / 2
                new_end = center + range_width / 2

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
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = None

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class TimelineControls(QWidget):
    """Main timeline control panel - now designed as an overlay"""
    close_requested = pyqtSignal()

    def __init__(self, total_days=90, parent=None):
        super().__init__(parent)
        self.total_days = total_days
        self.total_seconds = total_days * 24 * 60 * 60
        self.current_time = 0
        self.is_playing = False
        self.playback_speed = 1
        self.playback_direction = 'forward'
        self.visible_start = 0
        self.visible_end = self.total_seconds

        # Make this widget semi-transparent overlay with square corners
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            TimelineControls {
                background-color: rgba(0, 0, 0, 230);
                border-radius: 0px;
            }
        """)

        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top controls section
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-bottom: 1px solid rgba(255, 255, 255, 26);
            }
        """)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(24, 16, 24, 16)

        # Left - Playback controls
        playback_layout = QHBoxLayout()

        self.rewind_btn = QPushButton("⏪")
        self.rewind_btn.setToolTip("Toggle reverse playback")
        self.rewind_btn.clicked.connect(self.toggle_reverse)
        self.rewind_btn.setFixedSize(36, 36)

        self.skip_back_btn = QPushButton("⏮")
        self.skip_back_btn.setToolTip("Skip back 1 hour")
        self.skip_back_btn.clicked.connect(self.skip_backward)
        self.skip_back_btn.setFixedSize(36, 36)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setToolTip("Play/Pause")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.play_pause_btn.setFixedSize(48, 48)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                border-radius: 24px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)

        self.skip_forward_btn = QPushButton("⏭")
        self.skip_forward_btn.setToolTip("Skip forward 1 hour")
        self.skip_forward_btn.clicked.connect(self.skip_forward)
        self.skip_forward_btn.setFixedSize(36, 36)

        self.fast_forward_btn = QPushButton("⏩")
        self.fast_forward_btn.setToolTip("Toggle forward playback")
        self.fast_forward_btn.clicked.connect(self.toggle_forward)
        self.fast_forward_btn.setFixedSize(36, 36)

        speed_label = QLabel("Speed:")
        speed_label.setStyleSheet("color: rgba(255, 255, 255, 153);")

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x", "5x", "10x", "50x", "100x", "400x", "1000x", "5000x"])
        self.speed_combo.setCurrentIndex(2)
        self.speed_combo.currentTextChanged.connect(self.change_speed)
        self.speed_combo.setFixedWidth(80)

        playback_layout.addWidget(self.rewind_btn)
        playback_layout.addWidget(self.skip_back_btn)
        playback_layout.addWidget(self.play_pause_btn)
        playback_layout.addWidget(self.skip_forward_btn)
        playback_layout.addWidget(self.fast_forward_btn)
        playback_layout.addSpacing(16)
        playback_layout.addWidget(speed_label)
        playback_layout.addWidget(self.speed_combo)
        playback_layout.addStretch()

        # Center - Time display
        time_layout = QVBoxLayout()
        self.time_label = QLabel(self.format_time(0))
        self.time_label.setStyleSheet("color: white; font-size: 20px; font-family: monospace;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.date_label = QLabel(self.format_date(0))
        self.date_label.setStyleSheet("color: rgba(255, 255, 255, 128); font-size: 11px;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.date_label)

        # Right - Zoom controls
        zoom_layout = QHBoxLayout()

        self.zoom_out_btn = QPushButton("🔍-")
        self.zoom_out_btn.setToolTip("Zoom out")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_out_btn.setFixedSize(36, 36)

        self.zoom_label = QLabel("1.0x")
        self.zoom_label.setStyleSheet("color: rgba(255, 255, 255, 153); min-width: 60px;")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.setToolTip("Zoom in")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_in_btn.setFixedSize(36, 36)

        jump_label = QLabel("Jump to day:")
        jump_label.setStyleSheet("color: rgba(255, 255, 255, 153);")

        self.day_spinner = QSpinBox()
        self.day_spinner.setRange(0, self.total_days)
        self.day_spinner.setValue(0)
        self.day_spinner.valueChanged.connect(self.jump_to_day)
        self.day_spinner.setFixedWidth(80)

        zoom_layout.addStretch()
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addWidget(self.zoom_in_btn)
        zoom_layout.addSpacing(16)
        zoom_layout.addWidget(jump_label)
        zoom_layout.addWidget(self.day_spinner)

        controls_layout.addLayout(playback_layout)
        controls_layout.addLayout(time_layout)
        controls_layout.addLayout(zoom_layout)

        # Position slider
        position_frame = QFrame()
        position_frame.setStyleSheet("background-color: transparent;")
        position_layout = QHBoxLayout(position_frame)
        position_layout.setContentsMargins(24, 16, 24, 16)

        self.position_start_label = QLabel(self.format_time(0))
        self.position_start_label.setStyleSheet("color: rgba(255, 255, 255, 153); font-size: 11px;")
        self.position_start_label.setFixedWidth(110)

        self.position_slider = SimplePositionSlider()
        self.position_slider.value_changed.connect(self.position_slider_changed)
        self.position_slider.installEventFilter(self)

        self.position_end_label = QLabel(self.format_time(self.total_seconds))
        self.position_end_label.setStyleSheet("color: rgba(255, 255, 255, 153); font-size: 11px;")
        self.position_end_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.position_end_label.setFixedWidth(110)

        position_layout.addWidget(self.position_start_label)
        position_layout.addWidget(self.position_slider, 1)
        position_layout.addWidget(self.position_end_label)

        # Overview bar
        overview_frame = QFrame()
        overview_frame.setStyleSheet("background-color:  transparent;")
        overview_layout = QHBoxLayout(overview_frame)
        overview_layout.setContentsMargins(24, 8, 24, 24)

        start_label = QLabel("Day 0")
        start_label.setStyleSheet("color: rgba(255, 255, 255, 102); font-size: 11px;")
        start_label.setFixedWidth(110)

        self.overview_bar = OverviewBar()
        self.overview_bar.position_clicked.connect(self.overview_clicked)
        self.overview_bar.range_changed.connect(self.overview_range_changed)
        self.overview_bar.installEventFilter(self)

        end_label = QLabel(f"Day {self.total_days}")
        end_label.setStyleSheet("color: rgba(255, 255, 255, 102); font-size: 11px;")
        end_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        end_label.setFixedWidth(110)

        overview_layout.addWidget(start_label)
        overview_layout.addWidget(self.overview_bar, 1)
        overview_layout.addWidget(end_label)

        main_layout.addWidget(controls_frame)
        main_layout.addWidget(position_frame)
        main_layout.addWidget(overview_frame)

        self.setLayout(main_layout)
        self.update_ui()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.Wheel:
            if obj in [self.position_slider, self.overview_bar]:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True
        return super().eventFilter(obj, event)

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_playback)

    def format_time(self, seconds):
        days = int(seconds // (24 * 60 * 60))
        hours = int((seconds % (24 * 60 * 60)) // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"Day {days} {hours:02d}:{mins: 02d}:{secs:02d}"

    def format_date(self, seconds):
        start_date = datetime(2024, 1, 1)
        current_date = start_date + timedelta(seconds=seconds)
        return current_date.strftime("%b %d, %Y")

    def toggle_play_pause(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_pause_btn.setText("⏸")
            self.timer.start(1000)
        else:
            self.play_pause_btn.setText("▶")
            self.timer.stop()

    def update_playback(self):
        direction = 1 if self.playback_direction == 'forward' else -1
        new_time = self.current_time + direction * self.playback_speed

        # Keep within total bounds
        new_time = max(0, min(self.total_seconds, new_time))

        range_size = self.visible_end - self.visible_start

        # Check if we need to shift the viewport
        needs_shift = False

        if self.playback_direction == 'forward':
            # Forward:  if approaching the right edge, shift right
            if new_time > self.visible_end:
                shift = new_time - self.visible_end
                new_visible_end = min(self.total_seconds, self.visible_end + shift)
                new_visible_start = max(0, new_visible_end - range_size)
                # Adjust end to maintain range size
                new_visible_end = new_visible_start + range_size

                self.visible_start = new_visible_start
                self.visible_end = new_visible_end
                needs_shift = True
        else:
            # Backward: if approaching the left edge, shift left
            if new_time < self.visible_start:
                shift = self.visible_start - new_time
                new_visible_start = max(0, self.visible_start - shift)
                new_visible_end = min(self.total_seconds, new_visible_start + range_size)
                # Adjust start to maintain range size
                new_visible_start = new_visible_end - range_size

                self.visible_start = new_visible_start
                self.visible_end = new_visible_end
                needs_shift = True

        # Update current time (clamp to visible range if not shifting)
        if not needs_shift:
            self.current_time = max(self.visible_start, min(self.visible_end, new_time))
        else:
            self.current_time = new_time

        self.update_ui()

    def update_ui(self):
        self.time_label.setText(self.format_time(self.current_time))
        self.date_label.setText(self.format_date(self.current_time))

        self.position_start_label.setText(self.format_time(self.visible_start))
        self.position_end_label.setText(self.format_time(self.visible_end))

        if self.visible_end > self.visible_start:
            position_ratio = (self.current_time - self.visible_start) / (self.visible_end - self.visible_start)
        else:
            position_ratio = 0.0
        self.position_slider.set_position(position_ratio)

        range_normalized_start = self.visible_start / self.total_seconds
        range_normalized_end = self.visible_end / self.total_seconds
        position_normalized = self.current_time / self.total_seconds

        self.overview_bar.set_viewport(range_normalized_start, range_normalized_end)
        self.overview_bar.set_position(position_normalized)

        zoom = self.total_seconds / (
                self.visible_end - self.visible_start) if self.visible_end > self.visible_start else 1.0
        self.zoom_label.setText(f"{zoom:.1f}x")

        if self.playback_direction == 'backward':
            self.rewind_btn.setStyleSheet("color: #fbbf24;")
            self.fast_forward_btn.setStyleSheet("")
        else:
            self.rewind_btn.setStyleSheet("")
            self.fast_forward_btn.setStyleSheet("color: #4ade80;")

    def position_slider_changed(self, normalized_pos):
        self.current_time = self.visible_start + (normalized_pos * (self.visible_end - self.visible_start))
        self.update_ui()

    def overview_range_changed(self, normalized_start, normalized_end):
        self.visible_start = normalized_start * self.total_seconds
        self.visible_end = normalized_end * self.total_seconds
        self.current_time = max(self.visible_start, min(self.visible_end, self.current_time))
        self.update_ui()

    def skip_backward(self):
        self.current_time = max(self.visible_start, self.current_time - 3600)
        self.update_ui()

    def skip_forward(self):
        self.current_time = min(self.visible_end, self.current_time + 3600)
        self.update_ui()

    def toggle_reverse(self):
        self.playback_direction = 'backward'
        self.update_ui()

    def toggle_forward(self):
        self.playback_direction = 'forward'
        self.update_ui()

    def change_speed(self, text):
        self.playback_speed = float(text.replace('x', ''))

    def zoom_in(self):
        if self.visible_end <= self.visible_start:
            return
        playhead_ratio = (self.current_time - self.visible_start) / (self.visible_end - self.visible_start)
        current_range = self.visible_end - self.visible_start
        new_range = max(60, current_range / 2)
        new_start = self.current_time - (new_range * playhead_ratio)
        new_end = new_start + new_range
        if new_start < 0:
            new_start = 0
            new_end = new_range
        elif new_end > self.total_seconds:
            new_end = self.total_seconds
            new_start = new_end - new_range
        self.visible_start = new_start
        self.visible_end = new_end
        self.update_ui()

    def zoom_out(self):
        if self.visible_end <= self.visible_start:
            return
        playhead_ratio = (self.current_time - self.visible_start) / (self.visible_end - self.visible_start)
        current_range = self.visible_end - self.visible_start
        new_range = min(self.total_seconds, current_range * 2)
        new_start = self.current_time - (new_range * playhead_ratio)
        new_end = new_start + new_range
        if new_start < 0:
            new_start = 0
            new_end = new_range
        elif new_end > self.total_seconds:
            new_end = self.total_seconds
            new_start = new_end - new_range
        self.visible_start = new_start
        self.visible_end = new_end
        self.update_ui()

    def jump_to_day(self, day):
        self.current_time = day * 24 * 60 * 60
        self.current_time = max(self.visible_start, min(self.visible_end, self.current_time))
        self.update_ui()

    def overview_clicked(self, percent):
        new_time = percent * self.total_seconds
        self.current_time = max(0, min(self.total_seconds, new_time))
        self.update_ui()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conflict of Nations - Replay Analysis")
        self.setMinimumSize(1200, 800)

        # Apply dark theme
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(17, 24, 39))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(55, 65, 81))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        self.setPalette(palette)

        # Central widget with stack layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 204);
                border-bottom: 1px solid rgba(255, 255, 255, 26);
            }
        """)
        header.setFixedHeight(57)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 12, 24, 12)

        title = QLabel("Conflict of Nations - Replay Analysis")
        title.setStyleSheet("color: white; font-size: 20px;")

        header_controls = QHBoxLayout()

        skip_back_mini = QPushButton("⏮")
        skip_back_mini.setFixedSize(32, 32)

        self.play_pause_mini = QPushButton("▶")
        self.play_pause_mini.setFixedSize(40, 40)
        self.play_pause_mini.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)

        skip_forward_mini = QPushButton("⏭")
        skip_forward_mini.setFixedSize(32, 32)

        self.timeline_toggle = QPushButton("Timeline ▼")
        self.timeline_toggle.setFixedHeight(32)
        self.timeline_toggle.clicked.connect(self.toggle_timeline)
        self.timeline_toggle.setStyleSheet("""
            QPushButton {
                background-color:  rgba(255, 255, 255, 26);
                border-radius: 4px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 51);
            }
        """)

        header_controls.addWidget(skip_back_mini)
        header_controls.addWidget(self.play_pause_mini)
        header_controls.addWidget(skip_forward_mini)
        header_controls.addSpacing(16)
        header_controls.addWidget(self.timeline_toggle)

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(36, 36)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 26);
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 51);
            }
        """)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addLayout(header_controls)
        header_layout.addStretch()
        header_layout.addWidget(settings_btn)

        # Container for map and overlay
        self.map_container = QWidget()
        self.map_container.setStyleSheet("background-color: #1f2937;")
        container_layout = QVBoxLayout(self.map_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Map area
        self.map_area = QLabel("🗺️\n\nInteractive Map Canvas\n\nYour replay visualization will render here")
        self.map_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_area.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 102);
                font-size: 18px;
                background-color: #1f2937;
            }
        """)
        container_layout.addWidget(self.map_area)

        # Timeline controls overlay - initially hidden
        self.timeline_controls = TimelineControls(90, self.map_container)
        self.timeline_controls.hide()
        self.timeline_controls.close_requested.connect(self.hide_timeline)

        # Sync play/pause
        self.play_pause_mini.clicked.connect(self.timeline_controls.toggle_play_pause)
        skip_back_mini.clicked.connect(self.timeline_controls.skip_backward)
        skip_forward_mini.clicked.connect(self.timeline_controls.skip_forward)

        main_layout.addWidget(header)
        main_layout.addWidget(self.map_container, 1)

        central_widget.setLayout(main_layout)

    def resizeEvent(self, event):
        """Reposition timeline overlay when window is resized"""
        super().resizeEvent(event)
        if self.timeline_controls.isVisible():
            self.position_timeline_overlay()

    def position_timeline_overlay(self):
        """Position the timeline overlay at the bottom of the map container with no margins"""
        container_rect = self.map_container.rect()
        timeline_height = 280  # Adjusted height since close button is removed

        # No margins - overlay spans full width and sits at bottom
        overlay_rect = QRect(
            0,
            container_rect.height() - timeline_height,
            container_rect.width(),
            timeline_height
        )
        self.timeline_controls.setGeometry(overlay_rect)

    def toggle_timeline(self):
        """Toggle timeline overlay visibility"""
        if self.timeline_controls.isVisible():
            self.hide_timeline()
        else:
            self.show_timeline()

    def show_timeline(self):
        """Show the timeline overlay"""
        self.position_timeline_overlay()
        self.timeline_controls.show()
        self.timeline_controls.raise_()
        self.timeline_toggle.setText("Timeline ▲")

    def hide_timeline(self):
        """Hide the timeline overlay"""
        self.timeline_controls.hide()
        self.timeline_toggle.setText("Timeline ▼")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set application-wide stylesheet
    app.setStyleSheet("""
        QWidget {
            background-color: #111827;
            color: white;
        }
        QPushButton {
            background-color: rgba(255, 255, 255, 26);
            border:  none;
            border-radius:  4px;
            color: white;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 51);
        }
        QPushButton:disabled {
            opacity: 0.3;
        }
        QComboBox, QSpinBox {
            background-color: rgba(255, 255, 255, 26);
            border:  1px solid rgba(255, 255, 255, 51);
            border-radius: 4px;
            padding: 4px 8px;
            color: white;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #1f2937;
            selection-background-color: #2563eb;
        }
        QSlider::groove: horizontal {
            background:  rgba(255, 255, 255, 51);
            height: 12px;
            border-radius: 6px;
        }
        QSlider::handle:horizontal {
            background: white;
            width: 24px;
            height: 24px;
            margin: -6px 0;
            border-radius: 12px;
        }
        QSlider::handle:horizontal:hover {
            background: #e0e0e0;
        }
        QSlider::sub-page: horizontal {
            background: #2563eb;
            border-radius: 6px;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())