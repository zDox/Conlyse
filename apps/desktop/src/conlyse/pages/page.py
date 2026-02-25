from __future__ import annotations
from abc import abstractmethod
from abc import ABCMeta
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget


if TYPE_CHECKING:
    from conlyse.app import App



class QtABCMeta(ABCMeta, type(QWidget)):
    pass


class Page(QWidget, metaclass=QtABCMeta):
    HEADER = True
    def __init__(self, app: App, parent=None):
        super().__init__(parent)
        self.app = app

    @abstractmethod
    def setup(self, context):
        pass


    @abstractmethod
    def page_update(self, delta_time: float):
        pass

    @abstractmethod
    def clean_up(self):
        pass

    def page_render(self, dt: float):
        pass
