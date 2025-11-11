from conflict_interface.replay.replay import Replay


class ReplayManager:
    def __init__(self):
        self.replays: dict[str, Replay] = {}

    def add_replay(self, replay):
        self.replays.append(replay)

    def get_replays(self):
        return self.replays

    def clear_replays(self):
        self.replays = []