from __future__ import annotations

from typing import TYPE_CHECKING

from conlyse.pages.page import Page

if TYPE_CHECKING:
    from conlyse.app import App

class ProvinceListPage(Page):
    HEADER = True
    def __init__(self, app: App):
        super().__init__(app)

    def setup(self, context):
        pass

    def update(self):
        pass

    def clean_up(self):
        pass



