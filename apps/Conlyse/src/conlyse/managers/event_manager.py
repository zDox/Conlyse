from __future__ import annotations

import threading
from threading import Lock
from typing import Callable
from typing import Dict
from typing import List
from typing import TYPE_CHECKING
from typing import Type

from PySide6.QtCore import QObject, Signal as pyqtSignal, QMetaObject, Qt, Q_ARG

from conlyse.logger import get_logger
from conlyse.managers.events.event import Event

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()


class EventDispatcher(QObject):
    """Qt object to dispatch events on the main thread"""
    event_signal = pyqtSignal(object)  # Signal to emit events


class EventManager:
    def __init__(self, app: App):
        self._handlers: Dict[Type[Event], List[Callable]] = {}
        self._lock = Lock()
        self.app = app
        self._dispatcher = EventDispatcher()
        self._main_thread = threading.current_thread()

        # Connect the signal to handle events on the main thread
        self._dispatcher.event_signal.connect(
            self._handle_event_on_main_thread,
            Qt.ConnectionType.QueuedConnection
        )

    def subscribe(self, event_type: Type[Event], handler: Callable[[Event], None]) -> None:
        """Subscribe a handler to an event type (thread-safe)"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: Type[Event], handler: Callable[[Event], None]) -> None:
        """Unsubscribe a handler from an event type (thread-safe)"""
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                except ValueError:
                    pass

    def publish(self, event: Event) -> None:
        """
        Publish an event (thread-safe).
        If called from a non-main thread, the event will be queued to the main thread.
        """
        if threading.current_thread() != self._main_thread:
            # Queue event to main thread using Qt's signal mechanism
            self._dispatcher.event_signal.emit(event)
        else:
            # Already on main thread, execute directly
            self._execute_handlers(event)

    def _handle_event_on_main_thread(self, event: Event) -> None:
        """Handle event on the main Qt thread"""
        self._execute_handlers(event)

    def _execute_handlers(self, event: Event) -> None:
        """Execute all handlers for the given event"""
        # Get a copy of handlers while holding the lock
        with self._lock:
            handlers = self._handlers.get(type(event), []).copy()

        # Execute handlers without holding the lock
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(f"Error handling event {type(event).__name__}: {e}")

    async def publish_async(self, event: Event) -> None:
        """Publish an event asynchronously"""
        self.publish(event)
