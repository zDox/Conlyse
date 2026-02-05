from typing import Literal


class ReplayTimeline:
    def __init__(self, mode: Literal['r', 'w', 'a', 'rw'] = 'r'):
        self._mode: Literal['r', 'w', 'a', 'rw'] = mode
        self._open = False

    def open(self):
        if self._open:
            return
        pass

    def close(self):
        if not self._open:
            return
        pass

    def get_mode(self):
        pass

    def set_mode(self, mode: Literal['r', 'w', 'a', 'rw'] = 'r'):
        if self._open:
            self.close()
            self._mode = mode
            self.open()
        else:
            self._mode = mode


    def que_patch(self, ):
        pass
