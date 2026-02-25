from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.managers.events.event import Event


class ReplayOpenCompleteEvent(Event):
    def __init__(self, replay_file_path: str):
        super().__init__()
        self.replay_file_path = replay_file_path
