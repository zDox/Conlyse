from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app import App

class EventManager:
    def __init__(self, app: App):
        pass

    def handle_event(self, event):
        print(f"Handling event: {event}")

