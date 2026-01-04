"""
DockSystem for managing sidebars and bottom dock in ReplayPage.
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
from conlyse.widgets.dock_system.docks.dock import Dock
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

        # Dock registry: dock_type -> (dock_widget, dock_type, needs_ritf)
        self.docks: dict[DockType, Dock] = {}

    def setup(self,
              available_docks: set[DockType],
              dock_factory: Callable[[DockType], Dock]):
        """
        Setup the dock system with sidebars and bottom dock.

        Args:
            available_docks: set with available DockType values
            dock_factory: Callable that creates dock widgets from dockType
        """
        # Create bottom dock first (so we can get its default height for sidebars)
        self.bottom_dock_container = BottomDockContainer(
            parent=self.content_container,
            default_height=150,
            left_sidebar_button_width=40,  # Will be set after sidebars
            right_sidebar_button_width=40
        )

        # Create sidebars with bottom dock height callback
        self.left_sidebar = Sidebar(
            side="left",
            parent=self.content_container,
            button_width=40,
            dock_width=300,
            bottom_dock_height=150
        )

        self.right_sidebar = Sidebar(
            side="right",
            parent=self.content_container,
            button_width=40,
            dock_width=300,
            bottom_dock_height=150,
        )

        # Add docks based on availability
        for dock_type in available_docks:
            # Create dock widget
            dock_widget = dock_factory(dock_type)

            # Store dock
            self.docks[dock_type] = dock_widget

            # Get dock label
            label = self._get_dock_label(dock_type)


            if dock_type in [DockType.GAME_INFO, DockType.PROVINCE_INFO, DockType.ARMY_INFO]:
                # Left sidebar docks
                self.left_sidebar.add_dock(dock_type, label, dock_widget)
            elif dock_type in [DockType.EVENTS, DockType.CITY_LIST, DockType.ARMY_LIST]:
                # Right sidebar docks
                self.right_sidebar.add_dock(dock_type, label, dock_widget)

        if DockType.TIMELINE in available_docks:
            # Create dock widget
            dock_widget = dock_factory(DockType.TIMELINE)
            self.docks[DockType.TIMELINE] = dock_widget

            # Get dock label
            label = self._get_dock_label(DockType.TIMELINE)
            self.bottom_dock_container.add_content(DockType.TIMELINE, dock_widget)
            self._add_bottom_dock_button(DockType.TIMELINE, label)

        # Show sidebars
        self.left_sidebar.show()
        self.left_sidebar.raise_()
        self.right_sidebar.show()
        self.right_sidebar.raise_()

    def _add_bottom_dock_button(self, dock_type: DockType, label: str):
        """Add a button for bottom dock control to the left sidebar."""
        if not self.left_sidebar or not self.bottom_dock_container:
            return

        # Create callback that toggles the bottom dock and updates button state
        def make_callback(pid):
            def callback():
                self.bottom_dock_container.toggle_content(pid)
                # Update button checked state
                is_active = self.bottom_dock_container.get_active_dock() == pid
                self.left_sidebar.set_bottom_dock_button_checked(pid, is_active)
            return callback

        self.left_sidebar.add_bottom_dock_button(dock_type, label, make_callback(dock_type))

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


    def process_events(self, events: dict[ReplayHookTag, list[ReplayHookEvent]]):
        """
        Process replay events and route them to subscribed docks.

        Args:
            events: Dictionary of ReplayHookTag to list of events
        """
        for dock in self.docks.values():
            subscribed_events = {
                tag: evts for tag, evts in events.items()
                if tag in dock.subscribed_tags
            }
            if not subscribed_events:
                continue
            dock.process_events(subscribed_events)

    def update_geometries(self):
        """Update sidebar and bottom dock geometries."""
        if self.left_sidebar:
            self.left_sidebar.update_geometry()
        if self.right_sidebar:
            self.right_sidebar.update_geometry()
        if self.bottom_dock_container:
            self.bottom_dock_container.update_geometry()

    def get_dock(self, dock_type: DockType) -> QWidget | None:
        """Get a dock widget by its DockType."""
        if dock_type in self.docks:
            return self.docks[dock_type]
        return None

    def open_dock(self, dock_type: DockType):
        """Open a specific dock."""
        if dock_type not in self.docks:
            return

        # Determine which container and open it
        if dock_type == DockType.TIMELINE:
            self.bottom_dock_container.open_dock(dock_type)
        elif dock_type in [DockType.GAME_INFO, DockType.PROVINCE_INFO, DockType.ARMY_INFO]:
            self.left_sidebar.open_dock(dock_type)
        elif dock_type in [DockType.EVENTS, DockType.CITY_LIST, DockType.ARMY_LIST]:
            self.right_sidebar.open_dock(dock_type)

    def close_dock(self, dock_type: DockType):
        """Close a specific dock."""
        if dock_type not in self.docks:
            return

        # Determine which container and close it
        if dock_type == DockType.TIMELINE:
            if self.bottom_dock_container.get_active_dock() == dock_type:
                self.bottom_dock_container.close_dock()
        elif dock_type in [DockType.GAME_INFO, DockType.PROVINCE_INFO, DockType.ARMY_INFO]:
            if self.left_sidebar.get_active_dock() == dock_type:
                self.left_sidebar.close_dock()
        elif dock_type in [DockType.EVENTS, DockType.CITY_LIST, DockType.ARMY_LIST]:
            if self.right_sidebar.get_active_dock() == dock_type:
                self.right_sidebar.close_dock()

    def cleanup(self):
        """Clean up dock system resources."""
        # Clean up docks
        for dock_type, dock_widget in self.docks.items():
            if hasattr(dock_widget, 'cleanup'):
                dock_widget.cleanup()
            dock_widget.deleteLater()
        
        self.docks.clear()

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
