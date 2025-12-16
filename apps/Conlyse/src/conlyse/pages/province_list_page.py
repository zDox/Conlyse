
from conlyse.pages.page import Page


class ProvinceListPage(Page):
    HEADER = True
    def __init__(self, app, parent=None):
        super().__init__(app, parent)

    def setup(self, context):
        pass

    def page_update(self, delta_time: float):
        pass

    def clean_up(self):
        pass


