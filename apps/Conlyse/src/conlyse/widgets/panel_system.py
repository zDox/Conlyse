"""
Panel System for managing sidebars and bottom panel in ReplayPage.
Handles panel lifecycle, event routing, and provides panels with replay interface access.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from PySide6.QtWidgets import QWidget

from conlyse.logger import get_logger
from conlyse.utils.enums import PanelType
from conlyse.widgets.bottom_panel import BottomPanel
from conlyse.widgets.sidebar import Sidebar

if TYPE_CHECKING:
    from conflict_interface.interface.replay_interface import ReplayInterface
    from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
    from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent

logger = get_logger()


class PanelSystem:
    """
    Manages the panel system including left/right sidebars and bottom panel.
    Routes replay events to panels and provides panels with ReplayInterface access.
    """
    
    def __init__(self, parent: QWidget, ritf: ReplayInterface, content_container: QWidget):
        """
        Initialize the panel system.
        
        Args:
            parent: Parent widget (typically the ReplayPage)
            ritf: ReplayInterface for providing to panels
            content_container: Container widget where sidebars/panels overlay
        """
        self.parent = parent
        self.ritf = ritf
        self.content_container = content_container
        
        # Sidebars and panels
        self.left_sidebar: Sidebar | None = None
        self.right_sidebar: Sidebar | None = None
        self.bottom_panel: BottomPanel | None = None
        
        # Panel registry: panel_name -> (panel_widget, panel_type, needs_ritf)
        self.panels: dict[str, tuple[QWidget, PanelType, bool]] = {}
        
        # Event subscriptions: ReplayHookTag -> set of panel_names
        self.event_subscriptions: dict[ReplayHookTag, set[str]] = {}
    
    def setup(self, 
              available_panels: dict[str, PanelType],
              panel_factory: Callable[[PanelType], QWidget],
              get_panel_ritf_requirement: Callable[[PanelType], bool] = None):
        """
        Setup the panel system with sidebars and bottom panel.
        
        Args:
            available_panels: Dictionary mapping panel IDs to PanelTypes
            panel_factory: Callable that creates panel widgets from PanelType
            get_panel_ritf_requirement: Optional callable to check if panel needs ritf
        """
        # Create bottom panel first (so we can get its default height for sidebars)
        self.bottom_panel = BottomPanel(
            parent=self.content_container,
            default_height=150,
            left_sidebar_width_callback=None,  # Will be set after sidebars
            right_sidebar_width_callback=None
        )
        
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
        
        # Update bottom panel with sidebar width callbacks
        self.bottom_panel.left_sidebar_width_callback = lambda: self.left_sidebar.get_current_width() if self.left_sidebar else 0
        self.bottom_panel.right_sidebar_width_callback = lambda: self.right_sidebar.get_current_width() if self.right_sidebar else 0
        
        # Add panels based on availability
        for panel_id, panel_type in available_panels.items():
            # Check if panel needs ritf
            needs_ritf = False
            if get_panel_ritf_requirement:
                needs_ritf = get_panel_ritf_requirement(panel_type)
            
            # Create panel widget
            panel_widget = panel_factory(panel_type)
            
            # Provide ritf to panel if it needs it
            if needs_ritf and hasattr(panel_widget, 'set_replay_interface'):
                panel_widget.set_replay_interface(self.ritf)
            
            # Store panel
            self.panels[panel_id] = (panel_widget, panel_type, needs_ritf)
            
            # Get panel label
            label = self._get_panel_label(panel_type)
            
            # Add to appropriate location
            if panel_type == PanelType.TIMELINE:
                # Timeline goes to bottom panel
                self.bottom_panel.add_content(panel_id, panel_widget)
                # Add bottom panel button to left sidebar
                self._add_bottom_panel_button(panel_id, label)
            elif panel_type in [PanelType.GAME_INFO, PanelType.PROVINCE_INFO, PanelType.ARMY_INFO]:
                # Left sidebar panels
                self.left_sidebar.add_panel(panel_id, label, panel_widget)
            elif panel_type in [PanelType.EVENTS, PanelType.CITY_LIST, PanelType.ARMY_LIST]:
                # Right sidebar panels
                self.right_sidebar.add_panel(panel_id, label, panel_widget)
        
        # Show sidebars
        self.left_sidebar.show()
        self.left_sidebar.raise_()
        self.right_sidebar.show()
        self.right_sidebar.raise_()
    
    def _add_bottom_panel_button(self, panel_id: str, label: str):
        """Add a button for bottom panel control to the left sidebar."""
        if not self.left_sidebar or not self.bottom_panel:
            return
        
        # Create callback that toggles the bottom panel and updates button state
        def make_callback(pid):
            def callback():
                self.bottom_panel.toggle_content(pid)
                # Update button checked state
                is_active = self.bottom_panel.get_active_content() == pid
                self.left_sidebar.set_bottom_panel_button_checked(pid, is_active)
            return callback
        
        self.left_sidebar.add_bottom_panel_button(panel_id, label, make_callback(panel_id))
    
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
    
    def subscribe_panel_to_event(self, panel_id: str, hook_tag: ReplayHookTag):
        """
        Subscribe a panel to receive specific replay events.
        
        Args:
            panel_id: ID of the panel to subscribe
            hook_tag: ReplayHookTag to subscribe to
        """
        if panel_id not in self.panels:
            logger.warning(f"Cannot subscribe unknown panel '{panel_id}' to events")
            return
        
        if hook_tag not in self.event_subscriptions:
            self.event_subscriptions[hook_tag] = set()
        
        self.event_subscriptions[hook_tag].add(panel_id)
    
    def process_events(self, events: dict[ReplayHookTag, list[ReplayHookEvent]]):
        """
        Process replay events and route them to subscribed panels.
        
        Args:
            events: Dictionary of ReplayHookTag to list of events
        """
        for hook_tag, event_list in events.items():
            if hook_tag not in self.event_subscriptions:
                continue
            
            # Get panels subscribed to this event type
            subscribed_panels = self.event_subscriptions[hook_tag]
            
            for panel_id in subscribed_panels:
                if panel_id not in self.panels:
                    continue
                
                panel_widget, panel_type, needs_ritf = self.panels[panel_id]
                
                # Call panel's event handler if it has one
                if hasattr(panel_widget, 'handle_replay_events'):
                    panel_widget.handle_replay_events(hook_tag, event_list)
    
    def update_geometries(self):
        """Update sidebar and bottom panel geometries."""
        if self.left_sidebar:
            self.left_sidebar.update_geometry()
        if self.right_sidebar:
            self.right_sidebar.update_geometry()
        if self.bottom_panel:
            self.bottom_panel.update_geometry()
    
    def get_panel(self, panel_id: str) -> QWidget | None:
        """Get a panel widget by its ID."""
        if panel_id in self.panels:
            return self.panels[panel_id][0]
        return None
    
    def open_panel(self, panel_id: str):
        """Open a specific panel."""
        if panel_id not in self.panels:
            return
        
        panel_widget, panel_type, needs_ritf = self.panels[panel_id]
        
        # Determine which container and open it
        if panel_type == PanelType.TIMELINE:
            self.bottom_panel.open_content(panel_id)
        elif panel_type in [PanelType.GAME_INFO, PanelType.PROVINCE_INFO, PanelType.ARMY_INFO]:
            self.left_sidebar.open_panel(panel_id)
        elif panel_type in [PanelType.EVENTS, PanelType.CITY_LIST, PanelType.ARMY_LIST]:
            self.right_sidebar.open_panel(panel_id)
    
    def close_panel(self, panel_id: str):
        """Close a specific panel."""
        if panel_id not in self.panels:
            return
        
        panel_widget, panel_type, needs_ritf = self.panels[panel_id]
        
        # Determine which container and close it
        if panel_type == PanelType.TIMELINE:
            if self.bottom_panel.get_active_content() == panel_id:
                self.bottom_panel.close_content()
        elif panel_type in [PanelType.GAME_INFO, PanelType.PROVINCE_INFO, PanelType.ARMY_INFO]:
            if self.left_sidebar.get_active_panel() == panel_id:
                self.left_sidebar.close_panel()
        elif panel_type in [PanelType.EVENTS, PanelType.CITY_LIST, PanelType.ARMY_LIST]:
            if self.right_sidebar.get_active_panel() == panel_id:
                self.right_sidebar.close_panel()
    
    def cleanup(self):
        """Clean up panel system resources."""
        # Clean up panels
        for panel_id, (panel_widget, panel_type, needs_ritf) in self.panels.items():
            if hasattr(panel_widget, 'cleanup'):
                panel_widget.cleanup()
            panel_widget.deleteLater()
        
        self.panels.clear()
        self.event_subscriptions.clear()
        
        # Clean up widgets
        if self.left_sidebar:
            self.left_sidebar.deleteLater()
            self.left_sidebar = None
        if self.right_sidebar:
            self.right_sidebar.deleteLater()
            self.right_sidebar = None
        if self.bottom_panel:
            self.bottom_panel.deleteLater()
            self.bottom_panel = None
