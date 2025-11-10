from page_type import PageType
from pages.page import Page


class PageManager:
    def __init__(self):
        self.pages: dict[PageType, type] = {}

        self.current_page_type: PageType = PageType.ReplayListPage
        self.current_page: Page = ReplayListPage()

        self.next_page_type: PageType | None = None

        # Context is used to hold the args the current page passes to the next page
        self.context = {}

    def register_page(self, page_type: PageType, page_class: type):
        self.pages[page_type] = page_class

    def switch_to(self, next_page_type: PageType, **kwargs):
        if next_page_type not in self.pages:
            raise Exception(f"Page type {next_page_type} is not registered in PageManager")
        if next_page_type == self.current_page_type:
            return

    def _transition_page(self):
        self.current_page.clean_up()
        self.current_page: Page = self.pages[self.next_page_type]()
        self.current_page.setup(self.context)
        self.current_page_type = self.next_page_type
        self.next_page_type = None

    def update(self):
        if self.next_page_type is not None:
            self._transition_page()

        self.current_page.update()
