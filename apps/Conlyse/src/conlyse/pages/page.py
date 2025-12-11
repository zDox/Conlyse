from abc import abstractmethod
from abc import ABCMeta
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    pass


class QtABCMeta(ABCMeta, type(QWidget)):
    pass


class Page(QWidget, metaclass=QtABCMeta):
    HEADER = True
    def __init__(self, app, parent=None):
        super().__init__(parent)

    @abstractmethod
    def setup(self, context):
        pass


    @abstractmethod
    def page_update(self):
        pass

    @abstractmethod
    def clean_up(self):
        pass