from conflict_interface.replay.replay_patch import ReplayPatch


class ReplayCache:
    def __init__(self):
        self._patches = {}

    def add_patch(self, key: tuple[int, int], value: ReplayPatch):
        self._patches[key] = value

    def has_patch(self, key) -> bool:
        return key in self._patches

    def get_patch(self, key):
        return self._patches.get(key)

    def clear(self):
        self._patches.clear()