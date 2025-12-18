from __future__ import annotations

import time
from abc import abstractmethod
from datetime import timedelta
from typing import final

from PySide6.QtWidgets import QVBoxLayout, QWidget

from conflict_interface.interface.replay_interface import ReplayInterface
from conlyse.logger import get_logger
from conlyse.pages.page import Page
from conlyse.utils.enums import PageType, PanelType
from conlyse.widgets.panel_system import PanelSystem
from conlyse.widgets.timecontrol import TimelineControls

logger = get_logger()

class ReplayPage(Page):
    """
    Base page class for pages with an active replay.
    Handles timeline controls, optional panel system, and replay interaction.
    """
    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self.ritf: ReplayInterface = self.app.replay_manager.get_active_replay()
        self.timeline_controls: TimelineControls | None = None
        
        # Panel system (optional, enabled by subclasses)
        self.panel_system: PanelSystem | None = None
        self.content_container: QWidget | None = None
        self._use_panel_system = False  # Subclasses set this to True to enable panels

        if not self.ritf:
            logger.error(f"Replay not loaded for path: {self.app.replay_manager.active_replay_path}")
            self.app.page_manager.switch_to(PageType.ReplayListPage,
                                            error_message=f"Failed to load replay: {self.app.replay_manager.active_replay_path}")
            return

    def setup(self, context):
        """Initialize the page. Subclasses should call this via super().setup()"""
        if self._use_panel_system:
            self._setup_panel_system()
        else:
            self._setup_legacy_timeline()

    def _setup_panel_system(self):
        """Setup the full panel system with sidebars and bottom panel."""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create content container (where subclass content goes)
        self.content_container = QWidget(self)
        layout.addWidget(self.content_container)
        
        self.setLayout(layout)
        
        # Create panel system
        self.panel_system = PanelSystem(self, self.ritf, self.content_container)
        
        # Setup timeline controls
        self.setup_timeline_controls()
        
        # Get available panels and setup
        available_panels = self.get_available_panels()
        self.panel_system.setup(
            available_panels=available_panels,
            panel_factory=self.create_panel_widget,
            get_panel_ritf_requirement=self.panel_needs_replay_interface
        )
        
        # Setup event subscriptions
        self.setup_panel_event_subscriptions()

    def _setup_legacy_timeline(self):
        """Setup legacy timeline controls (for pages not using panel system)."""
        self.setup_timeline_controls_legacy()

    def get_available_panels(self) -> dict[str, PanelType]:
        """
        Return a dictionary of available panels for this page.
        Override this in subclasses that use the panel system.
        
        Returns:
            Dictionary mapping panel identifiers to PanelType enums.
        """
        return {}

    def create_panel_widget(self, panel_type: PanelType) -> QWidget:
        """
        Create and return a widget for the given panel type.
        Override this in subclasses that use the panel system.
        
        Args:
            panel_type: The type of panel to create
            
        Returns:
            Widget instance for the panel
        """
        return QWidget()
    
    def panel_needs_replay_interface(self, panel_type: PanelType) -> bool:
        """
        Determine if a panel needs access to the ReplayInterface.
        Override this in subclasses to specify which panels need ritf.
        
        Args:
            panel_type: The type of panel
            
        Returns:
            True if panel needs ReplayInterface, False otherwise
        """
        return False
    
    def setup_panel_event_subscriptions(self):
        """
        Setup event subscriptions for panels.
        Override this in subclasses to subscribe panels to specific events.
        """
        pass

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
        if self.panel_system:
            self.panel_system.cleanup()
            self.panel_system = None

    @final
    def setup_timeline_controls(self):
        """Set up the timeline controls in the bottom panel (for panel system)."""
        self.timeline_controls = TimelineControls(self.ritf, parent=self)
        self.timeline_controls.time_changed.connect(self._private_on_timeline_time_changed)

    @final
    def setup_timeline_controls_legacy(self):
        """Set up legacy timeline controls (for pages not using panel system)."""
        # This is empty for now - legacy pages can override if needed
        pass

    @abstractmethod
    def _on_replay_jump(self):
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
        self._on_replay_jump()
        
        # Process events through panel system if available
        if self.panel_system:
            hook_events = self.ritf.poll_events()
            self.panel_system.process_events(hook_events)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._use_panel_system:
            return
        # Update panel system geometries when page is resized
        if self.panel_system:
            self.panel_system.update_geometries()
