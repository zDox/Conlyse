from PySide6.QtWidgets import QWidget
from conflict_interface.hook_system.replay_hook_event import ReplayHookEvent
from conflict_interface.hook_system.replay_hook_tag import ReplayHookTag


class Dock(QWidget):
    subscribed_events: set[ReplayHookTag] = {}

    def process_events(self, events: dict[ReplayHookTag, list[ReplayHookEvent]]):
        raise NotImplementedError("Dock subscribed to events, but no process_events method implemented.")