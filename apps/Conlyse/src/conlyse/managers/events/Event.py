from abc import ABC
from datetime import UTC
from datetime import datetime


class Event(ABC):
    def __init__(self):
        self.timestamp = datetime.now(UTC)
        self.type = self.__class__.__name__

