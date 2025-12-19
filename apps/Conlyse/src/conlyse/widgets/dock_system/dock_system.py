"""
dock System for managing sidebars and bottom dock in ReplayPage.
Handles dock lifecycle, event routing, and provides docks with replay interface access.
"""
from typing import Callable

from PySide6.QtWidgets import QWidget

from conlyse.logger import get_logger
from conlyse.utils.enums import DockType

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent

from conlyse.widgets.dock_system.bottom_dock_container import BottomDockContainer
from conlyse.widgets.dock_system.sidebar import Sidebar

logger = get_logger()


class DockSystem:
    """
    Manages the dock system including left/right sidebars and bottom dock.
    Routes replay events to docks and provides docks with ReplayInterface access.
    """

    def __init__(self, parent: QWidget, ritf: ReplayInterface, content_container: QWidget):
        """
        Initialize the dock system.

        Args:
            parent: Parent widget (typically the ReplayPage)
            ritf: ReplayInterface for providing to docks
            content_container: Container widget where sidebars/docks overlay
        """
        self.parent = parent
        self.ritf = ritf
        self.content_container = content_container

        # Sidebars and docks
        self.left_sidebar: Sidebar | None = None
        self.right_sidebar: Sidebar | None = None
        self.bottom_dock_container: BottomDockContainer | None = None

        # Dock registry: dock_name -> (dock_widget, dock_type, needs_ritf)
        self.docks: dict[str, tuple[QWidget, DockType, bool]] = {}

        # Event subscriptions: ReplayHookTag -> set of dock_names
        self.event_subscriptions: dict[ReplayHookTag, set[str]] = {}

    def setup(self,
              available_docks: dict[str, DockType],
              dock_factory: Callable[[DockType], QWidget],
              get_dock_ritf_requirement: Callable[[DockType], bool] = None):
        """
        Setup the dock system with sidebars and bottom dock.

        Args:
            available_docks: Dictionary mapping dock IDs to dockTypes
            dock_factory: Callable that creates dock widgets from dockType
            get_dock_ritf_requirement: Optional callable to check if dock needs ritf
        """
        # Create bottom dock first (so we can get its default height for sidebars)
        self.bottom_dock_container = BottomDockContainer(
            parent=self.content_container,
            default_height=150,
            left_sidebar_width_callback=None,  # Will be set after sidebars
            right_sidebar_width_callback=None
        )

        # Create sidebars with bottom dock height callback
        self.left_sidebar = Sidebar(
            side="left",
            parent=self.content_container,
            button_width=40,
            dock_width=300,
            bottom_dock_height_callback=lambda: self.bottom_dock_container.get_default_height() if self.bottom_dock_container else 0
        )

        self.right_sidebar = Sidebar(
            side="right",
            parent=self.content_container,
            button_width=40,
            dock_width=300,
            bottom_dock_height_callback=lambda: self.bottom_dock_container.get_default_height() if self.bottom_dock_container else 0
        )

        # Update bottom dock with sidebar width callbacks
        self.bottom_dock_container.left_sidebar_width_callback = lambda: 40 if self.left_sidebar else 0
        self.bottom_dock_container.right_sidebar_width_callback = lambda: 40 if self.right_sidebar else 0

        # Add docks based on availability
        for dock_id, dock_type in available_docks.items():
            # Check if dock needs ritf
            needs_ritf = False
            if get_dock_ritf_requirement:
                needs_ritf = get_dock_ritf_requirement(dock_type)

            # Create dock widget
            dock_widget = dock_factory(dock_type)

            # Provide ritf to dock if it needs it
            if needs_ritf and hasattr(dock_widget, 'set_replay_interface'):
                dock_widget.set_replay_interface(self.ritf)

            # Store dock
            self.docks[dock_id] = (dock_widget, dock_type, needs_ritf)

            # Get dock label
            label = self._get_dock_label(dock_type)

            # Add to appropriate location
            if dock_type == DockType.TIMELINE:
                # Timeline goes to bottom dock
                self.bottom_dock_container.add_content(dock_id, dock_widget)
                # Add bottom dock button to left sidebar
                self._add_bottom_dock_button(dock_id, label)
            elif dock_type in [DockType.GAME_INFO, DockType.PROVINCE_INFO, DockType.ARMY_INFO]:
                # Left sidebar docks
                self.left_sidebar.add_dock(dock_id, label, dock_widget)
            elif dock_type in [DockType.EVENTS, DockType.CITY_LIST, DockType.ARMY_LIST]:
                # Right sidebar docks
                self.right_sidebar.add_dock(dock_id, label, dock_widget)

        # Show sidebars
        self.left_sidebar.show()
        self.left_sidebar.raise_()
        self.right_sidebar.show()
        self.right_sidebar.raise_()

    def _add_bottom_dock_button(self, dock_id: str, label: str):
        """Add a button for bottom dock control to the left sidebar."""
        if not self.left_sidebar or not self.bottom_dock_container:
            return

        # Create callback that toggles the bottom dock and updates button state
        def make_callback(pid):
            def callback():
                self.bottom_dock_container.toggle_content(pid)
                # Update button checked state
                is_active = self.bottom_dock_container.get_active_content() == pid
                self.left_sidebar.set_bottom_dock_button_checked(pid, is_active)
            return callback

        self.left_sidebar.add_bottom_dock_button(dock_id, label, make_callback(dock_id))

    def _get_dock_label(self, dock_type: DockType) -> str:
        """Get display label for a dock type."""
        labels = {
            DockType.GAME_INFO: "Game",
            DockType.PROVINCE_INFO: "Province",
            DockType.ARMY_INFO: "Army",
            DockType.EVENTS: "Events",
            DockType.CITY_LIST: "Cities",
            DockType.ARMY_LIST: "Armies",
            DockType.TIMELINE: "Timeline"
        }
        return labels.get(dock_type, "Unknown")

    def subscribe_dock_to_event(self, dock_id: str, hook_tag: ReplayHookTag):
        """
        Subscribe a dock to receive specific replay events.

        Args:
            dock_id: ID of the dock to subscribe
            hook_tag: ReplayHookTag to subscribe to
        """
        if dock_id not in self.docks:
            logger.warning(f"Cannot subscribe unknown dock '{dock_id}' to events")
            return

        if hook_tag not in self.event_subscriptions:
            self.event_subscriptions[hook_tag] = set()

        self.event_subscriptions[hook_tag].add(dock_id)

    def process_events(self, events: dict[ReplayHookTag, list[ReplayHookEvent]]):
        """
        Process replay events and route them to subscribed docks.

        Args:
            events: Dictionary of ReplayHookTag to list of events
        """
        for hook_tag, event_list in events.items():
            if hook_tag not in self.event_subscriptions:
                continue

            # Get docks subscribed to this event type
            subscribed_docks = self.event_subscriptions[hook_tag]

            for dock_id in subscribed_docks:
                if dock_id not in self.docks:
                    continue

                dock_widget, dock_type, needs_ritf = self.docks[dock_id]

                # Call dock's event handler if it has one
                if hasattr(dock_widget, 'handle_replay_events'):
                    dock_widget.handle_replay_events(hook_tag, event_list)

    def update_geometries(self):
        """Update sidebar and bottom dock geometries."""
        if self.left_sidebar:
            self.left_sidebar.update_geometry()
        if self.right_sidebar:
            self.right_sidebar.update_geometry()
        if self.bottom_dock_container:
            self.bottom_dock_container.update_geometry()

    def get_dock(self, dock_id: str) -> QWidget | None:
        """Get a dock widget by its ID."""
        if dock_id in self.docks:
            return self.docks[dock_id][0]
        return None

    def open_dock(self, dock_id: str):
        """Open a specific dock."""
        if dock_id not in self.docks:
            return

        dock_widget, dock_type, needs_ritf = self.docks[dock_id]

        # Determine which container and open it
        if dock_type == DockType.TIMELINE:
            self.bottom_dock_container.open_content(dock_id)
        elif dock_type in [DockType.GAME_INFO, DockType.PROVINCE_INFO, DockType.ARMY_INFO]:
            self.left_sidebar.open_dock(dock_id)
        elif dock_type in [DockType.EVENTS, DockType.CITY_LIST, DockType.ARMY_LIST]:
            self.right_sidebar.open_dock(dock_id)

    def close_dock(self, dock_id: str):
        """Close a specific dock."""
        if dock_id not in self.docks:
            return

        dock_widget, dock_type, needs_ritf = self.docks[dock_id]

        # Determine which container and close it
        if dock_type == DockType.TIMELINE:
            if self.bottom_dock_container.get_active_content() == dock_id:
                self.bottom_dock_container.close_content()
        elif dock_type in [DockType.GAME_INFO, DockType.PROVINCE_INFO, DockType.ARMY_INFO]:
            if self.left_sidebar.get_active_dock() == dock_id:
                self.left_sidebar.close_dock()
        elif dock_type in [DockType.EVENTS, DockType.CITY_LIST, DockType.ARMY_LIST]:
            if self.right_sidebar.get_active_dock() == dock_id:
                self.right_sidebar.close_dock()

    def cleanup(self):
        """Clean up dock system resources."""
        # Clean up docks
        for dock_id, (dock_widget, dock_type, needs_ritf) in self.docks.items():
            if hasattr(dock_widget, 'cleanup'):
                dock_widget.cleanup()
            dock_widget.deleteLater()
        
        self.docks.clear()
        self.event_subscriptions.clear()
        
        # Clean up widgets
        if self.left_sidebar:
            self.left_sidebar.deleteLater()
            self.left_sidebar = None
        if self.right_sidebar:
            self.right_sidebar.deleteLater()
            self.right_sidebar = None
        if self.bottom_dock_container:
            self.bottom_dock_container.deleteLater()
            self.bottom_dock_container = None
