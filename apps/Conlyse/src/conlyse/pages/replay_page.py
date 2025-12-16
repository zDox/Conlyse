from __future__ import annotations

import time
from abc import abstractmethod
from datetime import timedelta
from typing import final

from conflict_interface.interface.replay_interface import ReplayInterface
from conlyse.logger import get_logger
from conlyse.pages.page import Page
from conlyse.utils.enums import PageType
from conlyse.widgets.mui.button import CButton
from conlyse.widgets.timecontrol import TimelineControls

logger = get_logger()

class ReplayPage(Page):
    """
    Base page class for pages with an active replay.
    Handles timeline controls and replay interaction.
    """
    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self.ritf: ReplayInterface = self.app.replay_manager.get_active_replay()
        self.timeline_controls: TimelineControls | None = None
        self.timeline_button: CButton | None = None

        if not self.ritf:
            logger.error(f"Replay not loaded for path: {self.app.replay_manager.active_replay_path}")
            self.app.page_manager.switch_to(PageType.ReplayListPage,
                                            error_message=f"Failed to load replay: {self.app.replay_manager.active_replay_path}")
            return

    def setup(self, context):
        self.setup_timeline_controls()

    def page_update(self, delta_time: float):
        if self.timeline_controls:
            self.timeline_controls.advance_time(delta_time)

    def clean_up(self):
        if self.timeline_controls:
            self.timeline_controls.clean_up()
            self.timeline_controls.deleteLater()
            self.timeline_controls = None
        if self.timeline_button:
            self.timeline_button.deleteLater()
            self.timeline_button = None

    @final
    def setup_timeline_controls(self):
        """Set up the timeline panel and button."""
        self.timeline_controls = TimelineControls(self.ritf, parent=self)
        self.timeline_controls.setVisible(False)
        self.timeline_controls.time_changed.connect(self._private_on_timeline_time_changed)

        self._setup_timeline_button()

    @final
    def _setup_timeline_button(self):
        """Create and attach the header button that toggles the timeline panel."""
        self.timeline_button = CButton("Open Timeline", "contained", parent=self.app.main_window.header)
        self.timeline_button.clicked.connect(self.toggle_timeline_visibility)
        self.app.main_window.header.set_actions([self.timeline_button])

    @final
    def toggle_timeline_visibility(self):
        if not self.timeline_controls:
            return
        is_visible = self.timeline_controls.isVisible()
        new_visible_state = not is_visible
        self.timeline_controls.setVisible(new_visible_state)
        if new_visible_state:
            self._position_timeline_overlay()
            self.timeline_controls.raise_()
        if self.timeline_button:
            self.timeline_button.setText("Close Timeline" if new_visible_state else "Open Timeline")

    @abstractmethod
    def _on_replay_jump(self):
        """Handle any additional updates needed after a replay jump."""
        pass

    @final
    def _private_on_timeline_time_changed(self, current_time: float):
        if not self.ritf:
            return
        target_time = self.ritf.start_time + timedelta(seconds=current_time)
        self.ritf.jump_to(target_time)
        self._on_replay_jump()

    def _position_timeline_overlay(self):
        if not self.timeline_controls:
            return
        overlay_height = self.timeline_controls.sizeHint().height()
        self.timeline_controls.setGeometry(
            0,
            self.rect().height() - overlay_height,
            self.rect().width(),
            overlay_height,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_timeline_overlay()
