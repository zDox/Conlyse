from __future__ import annotations
from copy import deepcopy
from typing import TYPE_CHECKING
import time

from PySide6.QtWidgets import QStackedWidget

from conlyse.logger import get_logger
from conlyse.utils.enums import PageType
from conlyse.pages.page import Page

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()

class PageManager:
    """
    Manages the navigation and lifecycle of application pages.

    This class provides functionality to register, switch, and manage different pages
    within an application. It keeps track of navigation history, allowing backward and
    forward navigation, and controls the instantiation and setup of pages dynamically.
    It integrates with a stacked widget to handle page transitions.
    """
    def __init__(self, app: App):
        self.pages: dict[PageType, type] = {}

        self.current_page_type: PageType | None = None
        self.current_page: Page | None = None

        self.next_page_type: PageType | None = None

        self.app = app
        self.stack: QStackedWidget = app.main_window.stacked_widget  # QStackedWidget that holds the pages

        # Context is used to hold the args the current page passes to the next page
        self.context = {}

        # History tracking: list of (PageType, context) tuples
        self.history: list[tuple[PageType, dict]] = [(self.current_page_type, {})]
        self.history_index: int = 0

    def register_page(self, page_type: PageType, page_class: type):
        self.pages[page_type] = page_class

    def switch_to(self, next_page_type: PageType, **kwargs):
        """Schedule a page switch to the specified page type with optional context."""
        logger.debug(f"Scheduling switch to page {next_page_type} with context {kwargs}")
        if next_page_type not in self.pages:
            raise Exception(
                f"Page type {type(next_page_type)} {next_page_type} is not registered in PageManager {str(self.pages)} {[type(k) for k in self.pages.keys()]}."
            )
        if next_page_type == self.current_page_type and not self.current_page_type:
            return
        self.next_page_type = next_page_type
        self.context = kwargs

        # When switching to a new page (not through history navigation),
        # remove any forward history and add the new page
        self.history = self.history[:self.history_index + 1]
        self.history.append((next_page_type, kwargs.copy()))
        self.history_index += 1

    def go_back(self):
        """Navigate to the previous page in history."""
        if not self.can_go_back():
            return

        logger.debug(f"Going back from history index {self.history_index}")
        self.history_index -= 1
        page_type, context = self.history[self.history_index]
        self.next_page_type = page_type
        self.context = context.copy()

    def go_forward(self):
        """Navigate to the next page in history."""
        if not self.can_go_forward():
            return

        logger.debug(f"Going forward from history index {self.history_index}")
        self.history_index += 1
        page_type, context = self.history[self.history_index]
        self.next_page_type = page_type
        self.context = context.copy()

    def can_go_back(self) -> bool:
        """Check if backward navigation is possible."""
        return self.history_index > 0

    def can_go_forward(self) -> bool:
        """Check if forward navigation is possible."""
        return self.history_index < len(self.history) - 1

    def _transition_page(self):
        logger.debug(f"Transitioning to page {self.next_page_type} with context {self.context}")
        if self.current_page:
            self.current_page.clean_up()
            self.stack.removeWidget(self.current_page)
        # Create and setup new page
        previous_page_type = self.current_page_type
        self.current_page = self.pages[self.next_page_type](self.app, parent=self.stack)
        self.current_page_type = self.next_page_type
        self.next_page_type = None

        if self.current_page.HEADER:
            self.app.main_window.header.show()
        else:
            self.app.main_window.header.hide()

        logger.debug(f"Adding page {self.current_page_type} to stack")
        self.stack.addWidget(self.current_page)
        logger.debug(f"Setting current page to {self.current_page_type}")
        self.stack.setCurrentWidget(self.current_page)
        logger.debug(f"Updating style for page {self.current_page_type}")
        self.app.style_manager.update_style()
        self._last_update_time = time.perf_counter()


        # Manage in->out Replay transition
        if self.is_in_replay(previous_page_type) and self.out_replay:
            self.app.replay_manager.close_active_replay()
            self.setup_drawer(self.in_replay)
        elif self.is_out_replay(previous_page_type) and self.in_replay:
            self.setup_drawer(self.in_replay)



        context = deepcopy(self.context)
        self.context = {}
        logger.debug(f"Setting up page {self.current_page_type} with context {context}")
        self.current_page.setup(context)
        logger.debug(f"Completed setup for page {self.current_page_type}")

    def update(self, dt: float = 0.0):
        # If scheduled, perform it before delegating update to the current page.
        if self.next_page_type is not None:
            self._transition_page()

        if self.current_page:
            self.current_page.page_update(dt)

    def render(self, dt: float = 0.0):
        if self.current_page:
            self.current_page.page_render(dt)

    def get_current_page_type(self) -> PageType | None:
        return self.current_page_type

    @property
    def in_replay(self) -> bool:
        """Check if we are in Replay e.g. The user is visiting a Replay"""
        return self.current_page_type != PageType.ReplayListPage

    @staticmethod
    def is_in_replay(page_type: PageType) -> bool:
        return page_type != PageType.ReplayListPage

    @property
    def out_replay(self) -> bool:
        return self.current_page_type == PageType.ReplayListPage

    @staticmethod
    def is_out_replay(page_type: PageType) -> bool:
        return page_type == PageType.ReplayListPage

    def setup_drawer(self, in_replay: bool):
        """Setup the drawer entries based on whether we are in a replay or not."""
        self.app.main_window.drawer.clear_entries()
        self.app.main_window.drawer.register_entry("Replays", lambda: self.switch_to(PageType.ReplayListPage))
        if in_replay:
            self.app.main_window.drawer.register_entry("Map", lambda: self.switch_to(PageType.MapPage))
            self.app.main_window.drawer.register_entry("Players", lambda: self.switch_to(PageType.PlayerListPage))
