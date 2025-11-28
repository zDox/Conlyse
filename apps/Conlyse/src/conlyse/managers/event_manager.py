from __future__ import annotations

import threading
from threading import Lock
from typing import Callable
from typing import Dict
from typing import List
from typing import TYPE_CHECKING
from typing import Type

from conlyse.logger import get_logger
from conlyse.managers.events.event import Event

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()

class EventManager:
    def __init__(self, app: App):
        self._handlers: Dict[Type[Event], List[Callable]] = {}
        self._lock = Lock()
        self.app = app

    def subscribe(self, event_type: Type[Event], handler: Callable[[Event], None]) -> None:
        """Subscribe a handler to an event type"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: Type[Event], handler: Callable[[Event], None]) -> None:
        """Unsubscribe a handler from an event type"""
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                except ValueError:
                    pass

    def publish(self, event: Event) -> None:
        """Publish an event synchronously"""
        with self._lock:
            handlers = self._handlers.get(type(event), []).copy()

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(f"Error handling event {type(event).__name__}: {e}")

    async def publish_async(self, event: Event) -> None:
        """Publish an event asynchronously in a new thread"""
        self.publish(event)


