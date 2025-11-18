from conflict_interface.interface.replay_interface import ReplayInterface

from conlyse.managers.events.Event import Event


class ReplayLoadCompleteEvent(Event):
    def __init__(self, replay_file_path: str, replay_interface: ReplayInterface):
        super().__init__()
        self.replay_file_path = replay_file_path
        self.replay_interface = replay_interface
