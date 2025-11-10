from PyQt6.QtWidgets import QStackedWidget

from conlyse.utils.enums import PageType
from conlyse.pages.page import Page


class PageManager:
    """
    Manages the navigation and lifecycle of application pages.

    This class provides functionality to register, switch, and manage different pages
    within an application. It keeps track of navigation history, allowing backward and
    forward navigation, and controls the instantiation and setup of pages dynamically.
    It integrates with a stacked widget to handle page transitions.
    """
    def __init__(self, app):
        self.pages: dict[PageType, type] = {}

        self.current_page_type: PageType | None = None
        self.current_page: Page | None = None

        self.next_page_type: PageType | None = None

        self.app = app
        self.stack: QStackedWidget = app.q_window.stacked_widget  # QStackedWidget that holds the pages

        # Context is used to hold the args the current page passes to the next page
        self.context = {}

        # History tracking: list of (PageType, context) tuples
        self.history: list[tuple[PageType, dict]] = [(self.current_page_type, {})]
        self.history_index: int = 0

    def register_page(self, page_type: PageType, page_class: type):
        self.pages[page_type] = page_class

    def switch_to(self, next_page_type: PageType, **kwargs):
        if next_page_type not in self.pages:
            raise Exception(f"Page type {next_page_type} is not registered in PageManager")
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

        self.history_index -= 1
        page_type, context = self.history[self.history_index]
        self.next_page_type = page_type
        self.context = context.copy()

    def go_forward(self):
        """Navigate to the next page in history."""
        if not self.can_go_forward():
            return

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
        if self.current_page:
            self.current_page.clean_up()
            self.stack.removeWidget(self.current_page)

        # Create and setup new page
        self.current_page = self.pages[self.next_page_type](self.app)
        self.current_page.setup(self.context)
        self.current_page_type = self.next_page_type
        self.next_page_type = None

        self.stack.addWidget(self.current_page)
        self.stack.setCurrentWidget(self.current_page)
        self.app.style_manager.update_style()

        self.context = {}

    def update(self):
        # If scheduled, perform it before delegating update to the current page.
        if self.next_page_type is not None:
            self._transition_page()

        if self.current_page:
            self.current_page.update()

    def get_current_page_type(self) -> PageType | None:
        return self.current_page_type
