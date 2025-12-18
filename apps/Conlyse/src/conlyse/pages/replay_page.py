from __future__ import annotations

import time
from abc import abstractmethod
from datetime import timedelta
from typing import final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from conflict_interface.interface.replay_interface import ReplayInterface
from conlyse.logger import get_logger
from conlyse.pages.page import Page
from conlyse.utils.enums import PageType, PanelType
from conlyse.widgets.bottom_panel import BottomPanel
from conlyse.widgets.sidebar import Sidebar
from conlyse.widgets.timecontrol import TimelineControls

logger = get_logger()

class ReplayPage(Page):
    """
    Base page class for pages with an active replay.
    Handles timeline controls, optional sidebars, and replay interaction.
    """
    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self.ritf: ReplayInterface = self.app.replay_manager.get_active_replay()
        self.timeline_controls: TimelineControls | None = None
        
        # Sidebar and panel infrastructure (optional, enabled by subclasses)
        self.left_sidebar: Sidebar | None = None
        self.right_sidebar: Sidebar | None = None
        self.bottom_panel: BottomPanel | None = None
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
        
        # Create bottom panel first (so we can get its default height for sidebars)
        self.bottom_panel = BottomPanel(
            parent=self.content_container,
            default_height=150,
            left_sidebar_width_callback=None,  # Will be set after sidebars are created
            right_sidebar_width_callback=None
        )
        
        # Setup sidebars (after bottom panel so they can use its height)
        self.setup_sidebars()
        
        # Update bottom panel with sidebar width callbacks
        self.bottom_panel.left_sidebar_width_callback = lambda: self.left_sidebar.get_current_width() if self.left_sidebar else 0
        self.bottom_panel.right_sidebar_width_callback = lambda: self.right_sidebar.get_current_width() if self.right_sidebar else 0
        
        # Setup timeline controls as bottom panel content
        self.setup_timeline_controls()
        
        # Add bottom panel buttons to left sidebar
        self.setup_bottom_panel_buttons()

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

    @final
    def setup_sidebars(self):
        """Setup left and right sidebars with available panels."""
        if not self.content_container:
            return
        
        available_panels = self.get_available_panels()
        
        # Create sidebars with bottom panel height callback
        self.left_sidebar = Sidebar(
            side="left",
            parent=self.content_container,
            button_width=40,
            panel_width=300,
            bottom_panel_height_callback=lambda: self.bottom_panel.get_default_height() if self.bottom_panel else 0
        )
        
        self.right_sidebar = Sidebar(
            side="right",
            parent=self.content_container,
            button_width=40,
            panel_width=300,
            bottom_panel_height_callback=lambda: self.bottom_panel.get_default_height() if self.bottom_panel else 0
        )
        
        # Add panels based on availability
        for panel_id, panel_type in available_panels.items():
            if panel_type == PanelType.TIMELINE:
                # Timeline goes to bottom panel, not sidebars
                continue
            
            panel_widget = self.create_panel_widget(panel_type)
            label = self._get_panel_label(panel_type)
            
            # Determine which sidebar
            if panel_type in [PanelType.GAME_INFO, PanelType.PROVINCE_INFO, PanelType.ARMY_INFO]:
                self.left_sidebar.add_panel(panel_id, label, panel_widget)
            elif panel_type in [PanelType.EVENTS, PanelType.CITY_LIST, PanelType.ARMY_LIST]:
                self.right_sidebar.add_panel(panel_id, label, panel_widget)
        
        # Show sidebars
        self.left_sidebar.show()
        self.left_sidebar.raise_()
        self.right_sidebar.show()
        self.right_sidebar.raise_()

    @final
    def setup_bottom_panel_buttons(self):
        """Add bottom panel buttons to the left sidebar."""
        if not self.left_sidebar or not self.bottom_panel:
            return
        
        available_panels = self.get_available_panels()
        
        # Add buttons for bottom panel content (e.g., Timeline)
        for panel_id, panel_type in available_panels.items():
            if panel_type == PanelType.TIMELINE:
                label = self._get_panel_label(panel_type)
                # Create callback that toggles the bottom panel and updates button state
                def make_callback(pid):
                    def callback():
                        self.bottom_panel.toggle_content(pid)
                        # Update button checked state
                        is_active = self.bottom_panel.get_active_content() == pid
                        self.left_sidebar.set_bottom_panel_button_checked(pid, is_active)
                    return callback
                
                self.left_sidebar.add_bottom_panel_button(panel_id, label, make_callback(panel_id))

    @final
    def _get_panel_label(self, panel_type: PanelType) -> str:
        """Get display label for a panel type."""
        labels = {
            PanelType.GAME_INFO: "Game",
            PanelType.PROVINCE_INFO: "Province",
            PanelType.ARMY_INFO: "Army",
            PanelType.EVENTS: "Events",
            PanelType.CITY_LIST: "Cities",
            PanelType.ARMY_LIST: "Armies",
            PanelType.TIMELINE: "Timeline"
        }
        return labels.get(panel_type, "Unknown")

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
        if self.left_sidebar:
            self.left_sidebar.deleteLater()
            self.left_sidebar = None
        if self.right_sidebar:
            self.right_sidebar.deleteLater()
            self.right_sidebar = None
        if self.bottom_panel:
            self.bottom_panel.deleteLater()
            self.bottom_panel = None

    @final
    def setup_timeline_controls(self):
        """Set up the timeline controls in the bottom panel (for panel system)."""
        self.timeline_controls = TimelineControls(self.ritf, parent=self)
        self.timeline_controls.time_changed.connect(self._private_on_timeline_time_changed)
        
        # Add timeline to bottom panel if it's in available panels
        available_panels = self.get_available_panels()
        if PanelType.TIMELINE in available_panels.values():
            self.bottom_panel.add_content("timeline", self.timeline_controls)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._use_panel_system:
            return
        # Update sidebar geometries when page is resized
        if self.left_sidebar:
            self.left_sidebar.update_geometry()
        if self.right_sidebar:
            self.right_sidebar.update_geometry()
        # Update bottom panel position
        if self.bottom_panel:
            self.bottom_panel.update_geometry()
