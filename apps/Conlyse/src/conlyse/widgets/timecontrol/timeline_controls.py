from datetime import timedelta
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget
from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.widgets.mui.icon_button import CIconButton
from .overview_bar import OverviewBar
from .simple_position_slider import SimplePositionSlider

MIN_TIMELINE_DURATION_SECONDS = 1.0


class TimelineControls(QWidget):
    """Main timeline control panel."""

    close_requested = pyqtSignal()
    time_changed = pyqtSignal(float)

    def __init__(self, replay_interface: Optional[ReplayInterface], parent=None):
        super().__init__(parent)
        self.ritf: Optional[ReplayInterface] = replay_interface
        self.start_time = replay_interface.start_time
        self.last_time = replay_interface.last_time
        self.total_seconds = max((self.last_time - self.start_time).total_seconds(), MIN_TIMELINE_DURATION_SECONDS)
        self.total_days = int(self.total_seconds // (24 * 60 * 60))
        self.current_time = (replay_interface.client_time() - self.start_time).total_seconds()
        self.current_time = max(0.0, min(self.total_seconds, self.current_time))
        self.is_playing = False
        self.playback_speed = 1
        self.playback_direction = "forward"
        self.visible_start = 0
        self.visible_end = self.total_seconds
        self._last_emitted_time = self.current_time

        self.play_forward_btn = None
        self.skip_back_btn = None
        self.skip_forward_btn = None
        self.play_backward_btn: CIconButton | None = None
        self.play_pause_btn: CIconButton | None = None
        self.speed_combo = None
        self.time_label = None
        self.date_label = None
        self.position_start_label = None
        self.position_end_label = None
        self.position_slider = None
        self.overview_bar = None
        self.zoom_label = None
        self.zoom_in_btn = None
        self.zoom_out_btn = None
        self.day_spinner = None

        self.setup_ui()

    def setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(12, 8, 12, 8)

        # Left - Playback controls
        playback_layout = QHBoxLayout()

        self.play_backward_btn = CIconButton("fa6s.backward", "primary", parent=self)
        self.play_backward_btn.setToolTip("Toggle backward playback")
        self.play_backward_btn.clicked.connect(self.toggle_reverse)

        self.skip_back_btn = CIconButton("fa5s.step-backward", parent=self)
        self.skip_back_btn.setToolTip("Skip back 1 hour")
        self.skip_back_btn.clicked.connect(self.skip_backward)

        self.play_pause_btn = CIconButton("fa6s.play", parent=self)
        self.play_pause_btn.setToolTip("Play/Pause")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)

        self.skip_forward_btn = CIconButton("fa5s.step-forward", parent=self)
        self.skip_forward_btn.setToolTip("Skip forward 1 hour")
        self.skip_forward_btn.clicked.connect(self.skip_forward)

        self.play_forward_btn = CIconButton("fa6s.forward", "success",  parent=self)
        self.play_forward_btn.setToolTip("Toggle forward playback")
        self.play_forward_btn.clicked.connect(self.toggle_forward)

        speed_label = QLabel("Speed:", parent=self)

        self.speed_combo = QComboBox(parent=self)
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x", "5x", "10x", "50x", "100x", "400x", "1000x", "5000x"])
        self.speed_combo.setCurrentIndex(2)
        self.speed_combo.currentTextChanged.connect(self.change_speed)

        playback_layout.addWidget(self.play_backward_btn)
        playback_layout.addWidget(self.skip_back_btn)
        playback_layout.addWidget(self.play_pause_btn)
        playback_layout.addWidget(self.skip_forward_btn)
        playback_layout.addWidget(self.play_forward_btn)
        playback_layout.addSpacing(8)
        playback_layout.addWidget(speed_label)
        playback_layout.addWidget(self.speed_combo)
        playback_layout.addStretch()

        # Center - Time display
        time_layout = QVBoxLayout()
        self.time_label = QLabel(self.format_time(0), parent=self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.date_label = QLabel(self.format_date(0), parent=self)
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.date_label)

        # Right - Zoom controls
        zoom_layout = QHBoxLayout()

        self.zoom_out_btn = CIconButton("ei.zoom-out", parent=self)
        self.zoom_out_btn.setToolTip("Zoom out")
        self.zoom_out_btn.clicked.connect(self.zoom_out)

        self.zoom_label = QLabel("1.0x", parent=self)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.zoom_in_btn = CIconButton("ei.zoom-in", parent=self)
        self.zoom_in_btn.setToolTip("Zoom in")
        self.zoom_in_btn.clicked.connect(self.zoom_in)



        zoom_layout.addStretch()
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addWidget(self.zoom_in_btn)
        zoom_layout.addSpacing(8)

        controls_layout.addLayout(playback_layout)
        controls_layout.addLayout(time_layout)
        controls_layout.addLayout(zoom_layout)

        # Position slider
        position_frame = QFrame()
        position_layout = QHBoxLayout(position_frame)
        position_layout.setContentsMargins(12, 8, 12, 8)

        self.position_start_label = QLabel(self.format_time(0), parent=self)
        self.position_start_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.position_slider = SimplePositionSlider(parent=self)
        self.position_slider.value_changed.connect(self.position_slider_changed)
        self.position_slider.installEventFilter(self)

        self.position_end_label = QLabel(self.format_time(self.total_seconds), parent=self)
        self.position_end_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        position_layout.addWidget(self.position_start_label)
        position_layout.addWidget(self.position_slider, 1)
        position_layout.addWidget(self.position_end_label)

        # Overview bar
        overview_frame = QFrame()
        overview_layout = QHBoxLayout(overview_frame)
        overview_layout.setContentsMargins(12, 4, 12, 12)

        start_label = QLabel("Day 0", parent=self)

        self.overview_bar = OverviewBar(parent=self)
        self.overview_bar.position_clicked.connect(self.overview_clicked)
        self.overview_bar.range_changed.connect(self.overview_range_changed)
        self.overview_bar.installEventFilter(self)

        end_label = QLabel(f"Day {self.total_days}", parent=self)
        end_label.setAlignment(Qt.AlignmentFlag.AlignRight)

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

    def clean_up(self):
        """Cleanup resources when the controls are removed."""
        pass

    def format_time(self, seconds):
        days = int(seconds // (24 * 60 * 60))
        hours = int((seconds % (24 * 60 * 60)) // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"Day {days} {hours:02d}:{mins:02d}:{secs:02d}"

    def format_date(self, seconds):
        start_date = self.start_time
        current_date = start_date + timedelta(seconds=seconds)
        return current_date.strftime("%b %d, %Y")

    def toggle_play_pause(self):
        self.is_playing = not self.is_playing
        self.play_pause_btn.set_icon("fa6s.pause" if self.is_playing else "fa6s.play")

    def advance_time(self, delta_seconds: float):
        """Advance the timeline based on elapsed seconds (called externally)."""
        if not self.is_playing or delta_seconds <= 0:
            return
        direction = 1 if self.playback_direction == "forward" else -1
        new_time = self.current_time + direction * self.playback_speed * delta_seconds
        new_time = max(0.0, min(self.total_seconds, new_time))

        range_size = self.visible_end - self.visible_start

        if self.playback_direction == "forward":
            if new_time > self.visible_end:
                shift = new_time - self.visible_end
                new_visible_end = min(self.total_seconds, self.visible_end + shift)
                new_visible_start = max(0, new_visible_end - range_size)
                new_visible_end = new_visible_start + range_size

                self.visible_start = new_visible_start
                self.visible_end = new_visible_end
        else:
            if new_time < self.visible_start:
                shift = self.visible_start - new_time
                new_visible_start = max(0, self.visible_start - shift)
                new_visible_end = min(self.total_seconds, new_visible_start + range_size)
                new_visible_start = new_visible_end - range_size

                self.visible_start = new_visible_start
                self.visible_end = new_visible_end

        self.current_time = max(self.visible_start, min(self.visible_end, new_time))


        self.update_ui()

    def update_ui(self):
        if self.current_time != self._last_emitted_time:
            self.time_changed.emit(self.current_time)
            self._last_emitted_time = self.current_time

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

        zoom = self.total_seconds / (self.visible_end - self.visible_start) if self.visible_end > self.visible_start else 1.0
        self.zoom_label.setText(f"{zoom:.1f}x")

        if self.playback_direction == "backward":
            self.play_backward_btn.set_icon_color("warning")
            self.play_forward_btn.set_icon_color("primary")
        else:
            self.play_backward_btn.set_icon_color("primary")
            self.play_forward_btn.set_icon_color("success")

    def position_slider_changed(self, normalized_pos):
        self.current_time = self.visible_start + (normalized_pos * (self.visible_end - self.visible_start))
        self.update_ui()

    def overview_range_changed(self, normalized_start, normalized_end):
        self.visible_start = normalized_start * self.total_seconds
        self.visible_end = normalized_end * self.total_seconds
        self.current_time = max(self.visible_start, min(self.visible_end, self.current_time))
        self.update_ui()

    def skip(self, seconds: float):
        self.current_time = self.current_time + seconds
        self.visible_start = self.visible_start + seconds
        self.visible_end = self.visible_end + seconds
        self.update_ui()

    def skip_backward(self):
        self.skip(-3600)

    def skip_forward(self):
        self.skip(3600)
    def toggle_reverse(self):
        self.playback_direction = "backward"
        self.update_ui()

    def toggle_forward(self):
        self.playback_direction = "forward"
        self.update_ui()

    def change_speed(self, text):
        self.playback_speed = float(text.replace("x", ""))

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
        self.update_ui()

    def overview_clicked(self, percent):
        new_time = percent * self.total_seconds
        self.current_time = max(0, min(self.total_seconds, new_time))
        self.update_ui()
