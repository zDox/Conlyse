from abc import ABC, abstractmethod
from abc import ABCMeta
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from app import App


class QtABCMeta(ABCMeta, type(QWidget)):
    pass


class Page(QWidget, metaclass=QtABCMeta):
    def __init__(self, app):
        super().__init__()

    @abstractmethod
    def setup(self, context):
        pass


    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def clean_up(self):
        pass