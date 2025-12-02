from conlyse.pages.page import Page


class MapPage(Page):
    HEADER = True

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app

    def setup(self, context):
        self.setup_ui()

    def update(self):
        pass

    def clean_up(self):
        pass