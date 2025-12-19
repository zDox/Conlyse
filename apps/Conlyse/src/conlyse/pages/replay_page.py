from __future__ import annotations

import time
from abc import abstractmethod
from datetime import timedelta
from typing import final

from PySide6.QtWidgets import QVBoxLayout, QWidget
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag

from conflict_interface.interface.replay_interface import ReplayInterface
from conlyse.logger import get_logger
from conlyse.pages.page import Page
from conlyse.utils.enums import PageType, DockType
from conlyse.widgets.dock_system.dock_system import DockSystem
from conlyse.widgets.timecontrol import TimelineControls

logger = get_logger()

class ReplayPage(Page):
    """
    Base page class for pages with an active replay.
    Handles timeline controls, optional dock system, and replay interaction.
    """
    use_dock_system = False
    available_docks: set[DockType] = set()

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self.ritf: ReplayInterface = self.app.replay_manager.get_active_replay()
        self.timeline_controls: TimelineControls | None = None
        
        # Dock system (optional, enabled by subclasses)
        self.dock_system: DockSystem | None = None
        self.content_container: QWidget | None = None

        if not self.ritf:
            logger.error(f"Replay not loaded for path: {self.app.replay_manager.active_replay_path}")
            self.app.page_manager.switch_to(PageType.ReplayListPage,
                                            error_message=f"Failed to load replay: {self.app.replay_manager.active_replay_path}")
            return

    def setup(self, context):
        """Initialize the page. Subclasses should call this via super().setup()"""
        if self.use_dock_system:
            self._setup_dock_system()

    def _setup_dock_system(self):
        """Setup the full dock system with sidebars and bottom dock."""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create content container (where subclass content goes)
        self.content_container = QWidget(self)
        layout.addWidget(self.content_container)
        
        self.setLayout(layout)
        
        # Create dock system
        self.dock_system = DockSystem(self, self.ritf, self.content_container)
        
        # Setup timeline controls
        self.setup_timeline_controls()
        
        # setup
        self.dock_system.setup(
            available_docks=self.available_docks,
            dock_factory=self.create_dock_widget
        )


    def _setup_legacy_timeline(self):
        """Setup legacy timeline controls (for pages not using dock system)."""
        pass

    def create_dock_widget(self, dock_type: DockType) -> QWidget:
        """
        Create and return a widget for the given dock type.
        Override this in subclasses that use the dock system.
        
        Args:
            dock_type: The type of dock to create
            
        Returns:
            Widget instance for the dock
        """
        return QWidget()


    def page_update(self, delta_time: float):
        if self.timeline_controls:
            self.timeline_controls.advance_time(delta_time)

    def page_render(self, dt: float):
        pass

    def clean_up(self):
        if self.timeline_controls:
            self.timeline_controls.clean_up()
            self.timeline_controls.deleteLater()
            self.timeline_controls = None
        if self.dock_system:
            self.dock_system.cleanup()

    @final
    def setup_timeline_controls(self):
        """Set up the timeline controls in the bottom dock (for dock system)."""
        self.timeline_controls = TimelineControls(self.ritf, parent=self)
        self.timeline_controls.time_changed.connect(self._private_on_timeline_time_changed)


    @abstractmethod
    def _on_replay_jump(self, events: dict[ReplayHookTag, list[ReplayHookEvent]]):
        """Handle any additional updates needed after a replay jump."""
        pass

    @final
    def _private_on_timeline_time_changed(self, current_time: float):
        if not self.ritf:
            return
        target_time = self.ritf.start_time + timedelta(seconds=current_time)
        t1 = time.perf_counter()
        self.ritf.jump_to(target_time)
        t2 = time.perf_counter()
        self.app.performance_window.update_metric(
            "Last Jump Time", (t2 - t1) * 1000.0
        )
        events = self.ritf.poll_events()
        self._on_replay_jump(events)
        
        # Process events through dock system if available
        if self.dock_system:
            self.dock_system.process_events(events)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.use_dock_system:
            return
        # Update dock system geometries when page is resized
        if self.dock_system:
            self.dock_system.update_geometries()
