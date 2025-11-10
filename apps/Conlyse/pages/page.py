from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import App


class Page(ABC):
    def __init__(self, app):
        pass

    @abstractmethod
    def setup(self, context):
        pass


    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def clean_up(self):
        pass