from conlyse.managers.events.event import Event


class ReplayOpenFailedEvent(Event):
    def __init__(self, replay_file_path: str, error_message: str, trace_info: str):
        super().__init__()
        self.replay_file_path = replay_file_path
        self.error_message = error_message
        self.trace_info = trace_info